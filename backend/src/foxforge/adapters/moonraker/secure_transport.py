# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import socket
from urllib.parse import urlsplit

import aiohttp

from .control_transport import MoonrakerControlledHttpTransport
from .endpoint_policy import MoonrakerEndpointPolicy, MoonrakerEndpointSecurityError, MoonrakerPolicyResolver
from .http_transport import MoonrakerHttpSettings
from .transport import MoonrakerTransportError, MoonrakerTransportErrorKind


class MoonrakerSecuredHttpTransport(MoonrakerControlledHttpTransport):
    """Production Moonraker transport with DNS/address and redirect policy enforcement."""

    def __init__(
        self,
        settings: MoonrakerHttpSettings,
        *,
        endpoint_policy: MoonrakerEndpointPolicy | None = None,
    ) -> None:
        super().__init__(settings)
        self._endpoint_policy = endpoint_policy or MoonrakerEndpointPolicy()
        self._policy_resolver: MoonrakerPolicyResolver | None = None

    async def connect(self) -> None:
        if self._session is not None and not self._session.closed and self._ws is not None and not self._ws.closed:
            return

        await self._close_resources()
        self._events = asyncio.Queue()
        parts = urlsplit(self._settings.base_url)
        host = parts.hostname
        if not host:
            raise MoonrakerTransportError(
                MoonrakerTransportErrorKind.REJECTED,
                "Moonraker endpoint has no hostname",
                vendor_code="endpoint_policy",
            )
        port = parts.port or (443 if parts.scheme == "https" else 80)
        resolver = MoonrakerPolicyResolver(self._endpoint_policy)
        self._policy_resolver = resolver

        try:
            await resolver.resolve(host, port, socket.AF_UNSPEC)
            trace = aiohttp.TraceConfig()
            trace.on_request_redirect.append(_reject_redirect)
            connector = aiohttp.TCPConnector(resolver=resolver)
            headers = {"X-Api-Key": self._settings.api_key} if self._settings.api_key else None
            timeout = aiohttp.ClientTimeout(total=self._settings.request_timeout_seconds)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                connector=connector,
                trace_configs=[trace],
            )

            info = await self._get_printer_info()
            self._ws = await self._session.ws_connect(self._websocket_url())
            self._status = {}
            if str(info.get("state", "")).lower() == "ready":
                self._status = await self._subscribe(self._ws)
            self._state = self._compose_state(info=info, status=self._status, connected=True)
            self._listener_task = asyncio.create_task(self._listen())
        except MoonrakerEndpointSecurityError as error:
            await self._close_resources()
            raise MoonrakerTransportError(
                MoonrakerTransportErrorKind.REJECTED,
                str(error),
                vendor_code="endpoint_policy",
            ) from error
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

    async def _close_resources(self) -> None:
        await super()._close_resources()
        resolver = self._policy_resolver
        self._policy_resolver = None
        if resolver is not None:
            await resolver.close()


async def _reject_redirect(
    _session: aiohttp.ClientSession,
    _context: aiohttp.TraceConfigCtx,
    params: aiohttp.TraceRequestRedirectParams,
) -> None:
    raise MoonrakerEndpointSecurityError(
        f"Moonraker HTTP redirects are disabled by endpoint policy: HTTP {params.response.status}"
    )
