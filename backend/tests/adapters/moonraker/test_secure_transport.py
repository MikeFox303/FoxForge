# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

import pytest
from aiohttp import web

from foxforge.adapters.moonraker.endpoint_policy import MoonrakerEndpointPolicy
from foxforge.adapters.moonraker.http_transport import MoonrakerHttpSettings
from foxforge.adapters.moonraker.secure_transport import MoonrakerSecuredHttpTransport
from foxforge.adapters.moonraker.transport import MoonrakerTransportError, MoonrakerTransportErrorKind


async def _start_server(handler) -> tuple[web.AppRunner, str]:
    app = web.Application()
    app.router.add_get("/printer/info", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    assert site._server is not None  # noqa: SLF001 - test server needs the ephemeral port
    port = site._server.sockets[0].getsockname()[1]  # noqa: SLF001
    return runner, f"http://127.0.0.1:{port}"


def test_loopback_endpoint_is_blocked_without_explicit_override() -> None:
    async def scenario() -> None:
        async def info(_: web.Request) -> web.Response:
            return web.json_response({"state": "ready"})

        runner, base_url = await _start_server(info)
        transport = MoonrakerSecuredHttpTransport(MoonrakerHttpSettings(base_url))
        try:
            with pytest.raises(MoonrakerTransportError) as caught:
                await transport.connect()
            assert caught.value.kind == MoonrakerTransportErrorKind.REJECTED
            assert caught.value.vendor_code == "endpoint_policy"
        finally:
            await transport.disconnect()
            await runner.cleanup()

    asyncio.run(scenario())


def test_redirect_is_rejected_even_when_source_endpoint_is_allowed() -> None:
    async def scenario() -> None:
        async def redirect(_: web.Request) -> web.Response:
            raise web.HTTPFound("/redirect-target")

        runner, base_url = await _start_server(redirect)
        transport = MoonrakerSecuredHttpTransport(
            MoonrakerHttpSettings(base_url),
            endpoint_policy=MoonrakerEndpointPolicy(allow_loopback_endpoint=True),
        )
        try:
            with pytest.raises(MoonrakerTransportError) as caught:
                await transport.connect()
            assert caught.value.kind == MoonrakerTransportErrorKind.REJECTED
            assert caught.value.vendor_code == "endpoint_policy"
            assert "redirect" in caught.value.message.lower()
        finally:
            await transport.disconnect()
            await runner.cleanup()

    asyncio.run(scenario())


def test_embedded_url_credentials_are_rejected_before_network_access() -> None:
    async def scenario() -> None:
        transport = MoonrakerSecuredHttpTransport(
            MoonrakerHttpSettings("http://user:password@127.0.0.1:7125"),
            endpoint_policy=MoonrakerEndpointPolicy(allow_loopback_endpoint=True),
        )
        with pytest.raises(MoonrakerTransportError) as caught:
            await transport.connect()
        assert caught.value.kind == MoonrakerTransportErrorKind.REJECTED
        assert caught.value.vendor_code == "endpoint_policy"
        assert "credentials" in caught.value.message.lower()

    asyncio.run(scenario())
