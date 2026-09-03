# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Production Bambu LAN transport: MQTT state/control plus implicit FTPS upload."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import suppress
from pathlib import Path

from foxforge.domain.printers import utc_now

from .lan_codec import (
    BambuLanCodec,
    build_get_version_command,
    build_project_file_command,
    build_pushall_command,
    is_bambu_busy,
)
from .lan_wire import (
    BambuFtpsWire,
    BambuLanSettings,
    BambuMqttWire,
    ImplicitFtpsBambuWire,
    PahoBambuMqttWire,
)
from .native import BambuNativeDispatchResult, BambuNativePrintRequest, BambuNativeState
from .transport import BambuTransportError, BambuTransportErrorKind


class BambuLanTransport:
    """Bambu local-LAN transport with conservative print-start semantics."""

    def __init__(
        self,
        settings: BambuLanSettings,
        *,
        mqtt_wire: BambuMqttWire | None = None,
        ftps_wire: BambuFtpsWire | None = None,
    ) -> None:
        self._settings = settings
        self._mqtt = mqtt_wire or PahoBambuMqttWire(settings)
        self._ftps = ftps_wire or ImplicitFtpsBambuWire(settings)
        self._codec = BambuLanCodec()
        self._events: asyncio.Queue[BambuNativeState | BambuTransportError | None] = asyncio.Queue()
        self._pump_task: asyncio.Task[None] | None = None
        self._initial_state = asyncio.Event()
        self._sequence = 0
        self._responses: dict[tuple[str, str, str], asyncio.Future[Mapping[str, object]]] = {}

    async def connect(self) -> None:
        if self._pump_task is not None and not self._pump_task.done() and self._codec.state.connected:
            return
        self._events = asyncio.Queue()
        self._initial_state = asyncio.Event()
        try:
            await self._mqtt.connect()
        except BambuTransportError:
            raise
        self._codec.mark_connected(True)
        self._pump_task = asyncio.create_task(self._pump_messages())
        try:
            await self._mqtt.publish(build_get_version_command(self._next_sequence()))
            await self._mqtt.publish(build_pushall_command(self._next_sequence()))
            await asyncio.wait_for(
                self._initial_state.wait(),
                timeout=self._settings.connect_timeout_seconds,
            )
        except TimeoutError as error:
            await self.disconnect()
            raise BambuTransportError(
                BambuTransportErrorKind.TIMEOUT,
                "Bambu MQTT connected but no initial push_status was received",
            ) from error
        except BambuTransportError:
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        task = self._pump_task
        self._pump_task = None
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await self._mqtt.disconnect()
        state = self._codec.mark_connected(False)
        self._events.put_nowait(state)
        self._events.put_nowait(None)
        for future in self._responses.values():
            if not future.done():
                future.set_exception(
                    BambuTransportError(BambuTransportErrorKind.UNAVAILABLE, "Bambu transport disconnected")
                )
        self._responses.clear()

    def snapshot(self) -> BambuNativeState:
        return self._codec.state

    async def events(self) -> AsyncIterator[BambuNativeState]:
        queue = self._events
        while True:
            item = await queue.get()
            if item is None:
                return
            if isinstance(item, BambuTransportError):
                raise item
            yield item

    async def submit_print(self, request: BambuNativePrintRequest) -> BambuNativeDispatchResult:
        if not self._codec.state.connected:
            raise BambuTransportError(BambuTransportErrorKind.UNAVAILABLE, "Bambu printer is not connected")
        if is_bambu_busy(self._codec.state):
            raise BambuTransportError(BambuTransportErrorKind.BUSY, "Bambu printer already has an active print")

        remote_filename = _safe_remote_filename(request.filename)
        await self._ftps.upload(request.local_path, remote_filename)

        if is_bambu_busy(self._codec.state):
            raise BambuTransportError(
                BambuTransportErrorKind.BUSY,
                "Bambu printer became busy while the project was uploading",
            )

        sequence_id = self._next_sequence()
        command = build_project_file_command(sequence_id, request, remote_filename)
        key = ("print", "project_file", sequence_id)
        loop = asyncio.get_running_loop()
        response_future: asyncio.Future[Mapping[str, object]] = loop.create_future()
        self._responses[key] = response_future

        try:
            try:
                await self._mqtt.publish(command)
            except BambuTransportError as error:
                if error.kind in {
                    BambuTransportErrorKind.TIMEOUT,
                    BambuTransportErrorKind.UNAVAILABLE,
                }:
                    raise BambuTransportError(
                        BambuTransportErrorKind.INDETERMINATE,
                        f"Bambu project_file publish became ambiguous: {error.message}",
                        vendor_code=error.vendor_code,
                    ) from error
                raise

            try:
                response = await asyncio.wait_for(
                    response_future,
                    timeout=self._settings.command_timeout_seconds,
                )
            except TimeoutError as error:
                raise BambuTransportError(
                    BambuTransportErrorKind.INDETERMINATE,
                    "Bambu accepted the MQTT QoS1 publish but did not confirm project_file before timeout",
                ) from error

            result = str(response.get("result", "")).strip().lower()
            if result not in {"success", "ok"}:
                reason = str(response.get("reason") or response.get("message") or result or "project_file rejected")
                kind = BambuTransportErrorKind.BUSY if "busy" in reason.lower() else BambuTransportErrorKind.REJECTED
                raise BambuTransportError(kind, reason, vendor_code=_response_vendor_code(response))

            vendor_job_id = _response_job_id(response) or self._codec.state.vendor_job_id
            return BambuNativeDispatchResult(accepted_at=utc_now(), vendor_job_id=vendor_job_id)
        finally:
            self._responses.pop(key, None)

    async def _pump_messages(self) -> None:
        try:
            async for payload in self._mqtt.messages():
                self._resolve_response(payload)
                state = self._codec.apply(payload)
                if state is None:
                    continue
                if state.gcode_state is not None:
                    self._initial_state.set()
                self._events.put_nowait(state)
        except asyncio.CancelledError:
            raise
        except BambuTransportError as error:
            self._codec.mark_connected(False)
            self._events.put_nowait(error)
        except Exception as error:
            self._codec.mark_connected(False)
            self._events.put_nowait(BambuTransportError(BambuTransportErrorKind.INTERNAL, str(error)))

    def _resolve_response(self, payload: Mapping[str, object]) -> None:
        for section_name, section in payload.items():
            if not isinstance(section, Mapping):
                continue
            command = section.get("command")
            sequence_id = section.get("sequence_id")
            if not isinstance(command, str) or sequence_id is None:
                continue
            key = (str(section_name), command, str(sequence_id))
            future = self._responses.get(key)
            if future is not None and not future.done():
                future.set_result(section)

    def _next_sequence(self) -> str:
        self._sequence += 1
        return str(self._sequence)


def _safe_remote_filename(filename: str) -> str:
    basename = Path(filename).name
    if not basename or basename != filename or basename in {".", ".."}:
        raise BambuTransportError(BambuTransportErrorKind.REJECTED, "Bambu remote filename must be a plain basename")
    return basename


def _response_job_id(response: Mapping[str, object]) -> str | None:
    for key in ("subtask_id", "task_id"):
        value = response.get(key)
        if value not in {None, "", 0, "0"}:
            return str(value)
    return None


def _response_vendor_code(response: Mapping[str, object]) -> str | None:
    for key in ("code", "print_error", "reason"):
        value = response.get(key)
        if value not in {None, ""}:
            return str(value)
    return None
