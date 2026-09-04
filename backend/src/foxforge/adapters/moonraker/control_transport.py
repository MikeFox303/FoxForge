# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import aiohttp

from foxforge.domain.printers import utc_now

from .http_transport import MoonrakerHttpTransport
from .native import MoonrakerNativeJobControlAction, MoonrakerNativeJobControlResult
from .transport import MoonrakerTransportError, MoonrakerTransportErrorKind

_CONTROL_PATHS = {
    MoonrakerNativeJobControlAction.PAUSE: "/printer/print/pause",
    MoonrakerNativeJobControlAction.RESUME: "/printer/print/resume",
    MoonrakerNativeJobControlAction.CANCEL: "/printer/print/cancel",
}


class MoonrakerControlledHttpTransport(MoonrakerHttpTransport):
    """Extend the proven HTTP/WebSocket transport with guarded print controls."""

    async def control_print(
        self,
        action: MoonrakerNativeJobControlAction,
        expected_vendor_job_id: str,
    ) -> MoonrakerNativeJobControlResult:
        session = self._require_session()
        state = self._state
        if not state.connected:
            raise MoonrakerTransportError(MoonrakerTransportErrorKind.UNAVAILABLE, "Moonraker is not connected")
        if not state.filename or state.filename != expected_vendor_job_id:
            raise MoonrakerTransportError(
                MoonrakerTransportErrorKind.REJECTED,
                "Moonraker active job identity changed before the control command was sent",
                vendor_code="job_mismatch",
            )

        path = _CONTROL_PATHS[action]
        try:
            async with session.post(self._url(path)) as response:
                payload = await _response_payload(response)
                if response.status < 200 or response.status >= 300:
                    if response.status >= 500:
                        raise MoonrakerTransportError(
                            MoonrakerTransportErrorKind.INDETERMINATE,
                            f"Moonraker returned HTTP {response.status} after {action.value} request",
                            vendor_code=str(response.status),
                        )
                    raise self._http_error(response.status, payload)
        except MoonrakerTransportError:
            raise
        except TimeoutError as error:
            raise MoonrakerTransportError(
                MoonrakerTransportErrorKind.INDETERMINATE,
                f"Moonraker {action.value} timed out after the request may have been received",
            ) from error
        except aiohttp.ClientError as error:
            raise MoonrakerTransportError(
                MoonrakerTransportErrorKind.INDETERMINATE,
                f"Moonraker connection failed during {action.value}: {error}",
            ) from error

        return MoonrakerNativeJobControlResult(accepted_at=utc_now())


async def _response_payload(response: aiohttp.ClientResponse) -> object:
    try:
        return await response.json(content_type=None)
    except (ValueError, aiohttp.ContentTypeError):
        return await response.text()
