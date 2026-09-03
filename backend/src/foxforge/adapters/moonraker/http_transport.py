# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Concrete Moonraker HTTP/WebSocket transport.

This module owns Moonraker wire semantics. The rest of FoxForge consumes only
Moonraker-native DTOs through the ``MoonrakerTransport`` protocol.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import aiohttp

from foxforge.domain.printers import utc_now

from .native import MoonrakerNativeDispatchResult, MoonrakerNativePrintRequest, MoonrakerNativeState
from .transport import MoonrakerTransportError, MoonrakerTransportErrorKind

_SUBSCRIPTION_OBJECTS: dict[str, list[str]] = {
    "webhooks": ["state", "state_message"],
    "print_stats": ["filename", "print_duration", "state", "message"],
    "virtual_sdcard": ["progress"],
}


@dataclass(frozen=True, slots=True)
class MoonrakerHttpSettings:
    base_url: str
    api_key: str | None = None
    request_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        raw = self.base_url.strip().rstrip("/")
        parts = urlsplit(raw)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("base_url must be an absolute http:// or https:// URL")
        if parts.query or parts.fragment:
            raise ValueError("base_url must not contain query parameters or a fragment")
        if self.request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive")
        object.__setattr__(self, "base_url", raw)


class MoonrakerHttpTransport:
    """Moonraker transport using HTTP for files/control and WebSocket for state."""

    def __init__(self, settings: MoonrakerHttpSettings) -> None:
        self._settings = settings
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._events: asyncio.Queue[MoonrakerNativeState | MoonrakerTransportError | None] = asyncio.Queue()
        self._rpc_id = 0
        self._status: dict[str, dict[str, object]] = {}
        self._state = MoonrakerNativeState(
            connected=False,
            klippy_state="disconnected",
            klippy_message=None,
            print_state=None,
            filename=None,
            progress=None,
            print_duration_seconds=None,
            print_message=None,
            observed_at=utc_now(),
        )

    async def connect(self) -> None:
        if self._session is not None and not self._session.closed and self._ws is not None and not self._ws.closed:
            return

        await self._close_resources()
        self._events = asyncio.Queue()
        headers = {"X-Api-Key": self._settings.api_key} if self._settings.api_key else None
        timeout = aiohttp.ClientTimeout(total=self._settings.request_timeout_seconds)
        self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)

        try:
            info = await self._get_printer_info()
            self._ws = await self._session.ws_connect(self._websocket_url())
            self._status = {}
            if str(info.get("state", "")).lower() == "ready":
                self._status = await self._subscribe(self._ws)
            self._state = self._compose_state(info=info, status=self._status, connected=True)
            self._listener_task = asyncio.create_task(self._listen())
        except MoonrakerTransportError:
            await self._close_resources()
            raise
        except TimeoutError as error:
            await self._close_resources()
            raise MoonrakerTransportError(
                MoonrakerTransportErrorKind.TIMEOUT,
                "Moonraker connection timed out",
            ) from error
        except aiohttp.ClientResponseError as error:
            await self._close_resources()
            raise self._http_exception(error.status, str(error)) from error
        except aiohttp.ClientError as error:
            await self._close_resources()
            raise MoonrakerTransportError(MoonrakerTransportErrorKind.UNAVAILABLE, str(error)) from error
        except Exception as error:
            await self._close_resources()
            raise MoonrakerTransportError(MoonrakerTransportErrorKind.INTERNAL, str(error)) from error

    async def disconnect(self) -> None:
        if self._session is None and self._ws is None and self._listener_task is None:
            return
        task = self._listener_task
        self._listener_task = None
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await self._close_resources()
        self._state = replace(self._state, connected=False, observed_at=utc_now())
        self._events.put_nowait(None)

    def snapshot(self) -> MoonrakerNativeState:
        return self._state

    async def events(self) -> AsyncIterator[MoonrakerNativeState]:
        queue = self._events
        while True:
            item = await queue.get()
            if item is None:
                return
            if isinstance(item, MoonrakerTransportError):
                raise item
            yield item

    async def submit_print(self, request: MoonrakerNativePrintRequest) -> MoonrakerNativeDispatchResult:
        session = self._require_session()
        if not self._state.connected:
            raise MoonrakerTransportError(MoonrakerTransportErrorKind.UNAVAILABLE, "Moonraker is not connected")

        upload = await self._upload_gcode(session, request)
        item = upload.get("item")
        uploaded_path = request.filename
        if isinstance(item, Mapping):
            candidate = item.get("path")
            if isinstance(candidate, str) and candidate:
                uploaded_path = candidate

        if upload.get("print_started") is not True:
            await self._start_print(session, uploaded_path)

        return MoonrakerNativeDispatchResult(accepted_at=utc_now(), vendor_job_id=uploaded_path)

    async def _get_printer_info(self) -> dict[str, object]:
        session = self._require_session()
        try:
            async with session.get(self._url("/printer/info")) as response:
                payload = await _response_payload(response)
                if response.status < 200 or response.status >= 300:
                    raise self._http_error(response.status, payload)
        except TimeoutError as error:
            raise MoonrakerTransportError(
                MoonrakerTransportErrorKind.TIMEOUT,
                "Moonraker printer info timed out",
            ) from error
        except aiohttp.ClientError as error:
            raise MoonrakerTransportError(MoonrakerTransportErrorKind.UNAVAILABLE, str(error)) from error
        if not isinstance(payload, dict):
            raise MoonrakerTransportError(MoonrakerTransportErrorKind.INTERNAL, "invalid /printer/info response")
        return payload

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse) -> dict[str, dict[str, object]]:
        request_id = self._next_rpc_id()
        await ws.send_json(
            {
                "jsonrpc": "2.0",
                "method": "printer.objects.subscribe",
                "params": {"objects": _SUBSCRIPTION_OBJECTS},
                "id": request_id,
            }
        )
        while True:
            message = await ws.receive(timeout=self._settings.request_timeout_seconds)
            payload = _websocket_payload(message)
            if payload is None:
                raise MoonrakerTransportError(MoonrakerTransportErrorKind.UNAVAILABLE, "Moonraker WebSocket closed")
            if payload.get("id") == request_id:
                if "error" in payload:
                    raise MoonrakerTransportError(
                        MoonrakerTransportErrorKind.REJECTED,
                        f"Moonraker subscription rejected: {payload['error']}",
                    )
                result = payload.get("result")
                if not isinstance(result, Mapping):
                    raise MoonrakerTransportError(MoonrakerTransportErrorKind.INTERNAL, "invalid subscription response")
                status = result.get("status", {})
                return _normalize_status(status)
            self._handle_notification(payload, emit=False)

    async def _listen(self) -> None:
        ws = self._ws
        if ws is None:
            return
        try:
            async for message in ws:
                payload = _websocket_payload(message)
                if payload is None:
                    raise MoonrakerTransportError(MoonrakerTransportErrorKind.UNAVAILABLE, "Moonraker WebSocket closed")
                method = payload.get("method")
                if method == "notify_klippy_ready":
                    await self._refresh_ready_state(ws)
                    continue
                if method == "notify_klippy_disconnected":
                    self._state = replace(
                        self._state,
                        connected=True,
                        klippy_state="disconnected",
                        klippy_message="Klippy disconnected from Moonraker",
                        observed_at=utc_now(),
                    )
                    self._events.put_nowait(self._state)
                    continue
                self._handle_notification(payload, emit=True)
            if self._listener_task is not None:
                self._events.put_nowait(
                    MoonrakerTransportError(MoonrakerTransportErrorKind.UNAVAILABLE, "Moonraker WebSocket closed")
                )
        except asyncio.CancelledError:
            raise
        except MoonrakerTransportError as error:
            self._events.put_nowait(error)
        except TimeoutError:
            self._events.put_nowait(
                MoonrakerTransportError(MoonrakerTransportErrorKind.TIMEOUT, "Moonraker WebSocket operation timed out")
            )
        except aiohttp.ClientError as error:
            self._events.put_nowait(MoonrakerTransportError(MoonrakerTransportErrorKind.UNAVAILABLE, str(error)))
        except Exception as error:
            self._events.put_nowait(MoonrakerTransportError(MoonrakerTransportErrorKind.INTERNAL, str(error)))

    async def _refresh_ready_state(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        info = await self._get_printer_info()
        status = await self._subscribe(ws)
        self._status = status
        self._state = self._compose_state(info=info, status=status, connected=True)
        self._events.put_nowait(self._state)

    def _handle_notification(self, payload: Mapping[str, object], *, emit: bool) -> None:
        if payload.get("method") != "notify_status_update":
            return
        params = payload.get("params")
        if not isinstance(params, list) or not params or not isinstance(params[0], Mapping):
            return
        update = _normalize_status(params[0])
        _merge_status(self._status, update)
        info = {
            "state": self._status.get("webhooks", {}).get("state", self._state.klippy_state),
            "state_message": self._status.get("webhooks", {}).get("state_message", self._state.klippy_message),
        }
        self._state = self._compose_state(info=info, status=self._status, connected=True)
        if emit:
            self._events.put_nowait(self._state)

    def _compose_state(
        self,
        *,
        info: Mapping[str, object],
        status: Mapping[str, Mapping[str, object]],
        connected: bool,
    ) -> MoonrakerNativeState:
        webhooks = status.get("webhooks", {})
        print_stats = status.get("print_stats", {})
        virtual_sdcard = status.get("virtual_sdcard", {})
        klippy_state = _optional_string(webhooks.get("state")) or _optional_string(info.get("state")) or "unknown"
        klippy_message = _optional_string(webhooks.get("state_message")) or _optional_string(info.get("state_message"))
        return MoonrakerNativeState(
            connected=connected,
            klippy_state=klippy_state,
            klippy_message=klippy_message,
            print_state=_optional_string(print_stats.get("state")),
            filename=_optional_string(print_stats.get("filename")),
            progress=_fraction(virtual_sdcard.get("progress")),
            print_duration_seconds=_nonnegative_float(print_stats.get("print_duration")),
            print_message=_optional_string(print_stats.get("message")),
            observed_at=utc_now(),
        )

    async def _upload_gcode(
        self,
        session: aiohttp.ClientSession,
        request: MoonrakerNativePrintRequest,
    ) -> dict[str, object]:
        try:
            with Path(request.local_path).open("rb") as handle:
                form = aiohttp.FormData()
                form.add_field("root", "gcodes")
                form.add_field("checksum", request.sha256)
                form.add_field("print", "false")
                form.add_field(
                    "file",
                    handle,
                    filename=request.filename,
                    content_type="application/octet-stream",
                )
                async with session.post(self._url("/server/files/upload"), data=form) as response:
                    payload = await _response_payload(response)
                    if response.status < 200 or response.status >= 300:
                        raise self._http_error(response.status, payload)
        except FileNotFoundError as error:
            raise MoonrakerTransportError(
                MoonrakerTransportErrorKind.REJECTED,
                "local G-code file does not exist",
            ) from error
        except TimeoutError as error:
            raise MoonrakerTransportError(MoonrakerTransportErrorKind.TIMEOUT, "Moonraker upload timed out") from error
        except aiohttp.ClientError as error:
            raise MoonrakerTransportError(MoonrakerTransportErrorKind.UNAVAILABLE, str(error)) from error
        if not isinstance(payload, dict):
            raise MoonrakerTransportError(MoonrakerTransportErrorKind.INTERNAL, "invalid Moonraker upload response")
        return payload

    async def _start_print(self, session: aiohttp.ClientSession, filename: str) -> None:
        try:
            async with session.post(self._url("/printer/print/start"), params={"filename": filename}) as response:
                payload = await _response_payload(response)
                if response.status < 200 or response.status >= 300:
                    if response.status >= 500:
                        raise MoonrakerTransportError(
                            MoonrakerTransportErrorKind.INDETERMINATE,
                            f"Moonraker returned HTTP {response.status} after print start request",
                            vendor_code=str(response.status),
                        )
                    raise self._http_error(response.status, payload)
        except MoonrakerTransportError:
            raise
        except TimeoutError as error:
            raise MoonrakerTransportError(
                MoonrakerTransportErrorKind.INDETERMINATE,
                "Moonraker print start timed out after the request may have been received",
            ) from error
        except aiohttp.ClientError as error:
            raise MoonrakerTransportError(
                MoonrakerTransportErrorKind.INDETERMINATE,
                f"Moonraker connection failed during print start: {error}",
            ) from error

    def _require_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            raise MoonrakerTransportError(MoonrakerTransportErrorKind.UNAVAILABLE, "Moonraker session is not connected")
        return self._session

    def _http_error(self, status: int, payload: object) -> MoonrakerTransportError:
        message = _payload_message(payload) or f"Moonraker returned HTTP {status}"
        if status in {401, 403}:
            kind = MoonrakerTransportErrorKind.AUTHENTICATION
        elif status in {408, 504}:
            kind = MoonrakerTransportErrorKind.TIMEOUT
        elif status in {409, 423}:
            kind = MoonrakerTransportErrorKind.BUSY
        elif 500 <= status <= 599:
            kind = MoonrakerTransportErrorKind.UNAVAILABLE
        else:
            kind = MoonrakerTransportErrorKind.REJECTED
        return MoonrakerTransportError(kind, message, vendor_code=str(status))

    def _http_exception(self, status: int, message: str) -> MoonrakerTransportError:
        return self._http_error(status, {"message": message})

    def _next_rpc_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    def _url(self, path: str) -> str:
        return f"{self._settings.base_url}{path}"

    def _websocket_url(self) -> str:
        parts = urlsplit(self._settings.base_url)
        scheme = "wss" if parts.scheme == "https" else "ws"
        path = f"{parts.path.rstrip('/')}/websocket"
        return urlunsplit((scheme, parts.netloc, path, "", ""))

    async def _close_resources(self) -> None:
        ws = self._ws
        self._ws = None
        if ws is not None and not ws.closed:
            await ws.close()
        session = self._session
        self._session = None
        if session is not None and not session.closed:
            await session.close()


def _normalize_status(value: object) -> dict[str, dict[str, object]]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, dict[str, object]] = {}
    for object_name, object_value in value.items():
        if isinstance(object_name, str) and isinstance(object_value, Mapping):
            result[object_name] = {str(key): item for key, item in object_value.items()}
    return result


def _merge_status(target: dict[str, dict[str, object]], update: Mapping[str, Mapping[str, object]]) -> None:
    for object_name, values in update.items():
        target.setdefault(object_name, {}).update(values)


def _websocket_payload(message: aiohttp.WSMessage) -> dict[str, object] | None:
    if message.type == aiohttp.WSMsgType.TEXT:
        try:
            payload = message.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}
    if message.type in {aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
        return None
    return {}


async def _response_payload(response: aiohttp.ClientResponse) -> object:
    try:
        return await response.json(content_type=None)
    except (ValueError, aiohttp.ContentTypeError):
        return await response.text()


def _payload_message(payload: object) -> str | None:
    if isinstance(payload, Mapping):
        for key in ("message", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, Mapping):
                nested = value.get("message")
                if isinstance(nested, str) and nested:
                    return nested
    if isinstance(payload, str) and payload:
        return payload
    return None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _fraction(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if 0.0 <= number <= 1.0 else None


def _nonnegative_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if number >= 0 else None
