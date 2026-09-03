# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from hashlib import sha256
from pathlib import Path

import pytest
from aiohttp import WSMsgType, web

from foxforge.adapters.moonraker import (
    MoonrakerHttpSettings,
    MoonrakerHttpTransport,
    MoonrakerNativePrintRequest,
    MoonrakerTransportError,
    MoonrakerTransportErrorKind,
)


class _MoonrakerTestServer:
    def __init__(self, *, api_key: str | None = None, start_delay: float = 0.0, send_update: bool = False) -> None:
        self.api_key = api_key
        self.start_delay = start_delay
        self.send_update = send_update
        self.runner: web.AppRunner | None = None
        self.base_url = ""
        self.subscription: dict[str, object] | None = None
        self.upload_fields: dict[str, str] = {}
        self.upload_bytes = b""
        self.upload_filename: str | None = None
        self.started_filename: str | None = None

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/printer/info", self._printer_info)
        app.router.add_get("/websocket", self._websocket)
        app.router.add_post("/server/files/upload", self._upload)
        app.router.add_post("/printer/print/start", self._start_print)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        assert site._server is not None  # noqa: SLF001 - test server needs the ephemeral port
        port = site._server.sockets[0].getsockname()[1]  # noqa: SLF001
        self.base_url = f"http://127.0.0.1:{port}"

    async def close(self) -> None:
        if self.runner is not None:
            await self.runner.cleanup()

    def _check_auth(self, request: web.Request) -> None:
        if self.api_key is not None:
            assert request.headers.get("X-Api-Key") == self.api_key

    async def _printer_info(self, request: web.Request) -> web.Response:
        self._check_auth(request)
        return web.json_response({"state": "ready", "state_message": "Printer is ready"})

    async def _websocket(self, request: web.Request) -> web.WebSocketResponse:
        self._check_auth(request)
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for message in ws:
            if message.type != WSMsgType.TEXT:
                continue
            payload = message.json()
            if payload.get("method") != "printer.objects.subscribe":
                continue
            self.subscription = payload
            await ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "eventtime": 1.0,
                        "status": {
                            "webhooks": {"state": "ready", "state_message": "Printer is ready"},
                            "print_stats": {
                                "state": "standby",
                                "filename": "",
                                "print_duration": 0.0,
                                "message": "",
                            },
                            "virtual_sdcard": {"progress": 0.0},
                        },
                    },
                }
            )
            if self.send_update:
                await ws.send_json(
                    {
                        "jsonrpc": "2.0",
                        "method": "notify_status_update",
                        "params": [
                            {
                                "print_stats": {
                                    "state": "printing",
                                    "filename": "job.gcode",
                                    "print_duration": 3.5,
                                },
                                "virtual_sdcard": {"progress": 0.2},
                            },
                            2.0,
                        ],
                    }
                )
        return ws

    async def _upload(self, request: web.Request) -> web.Response:
        self._check_auth(request)
        reader = await request.multipart()
        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == "file":
                self.upload_filename = part.filename
                self.upload_bytes = await part.read()
            else:
                self.upload_fields[str(part.name)] = await part.text()
        return web.json_response(
            {
                "item": {
                    "path": self.upload_filename,
                    "root": "gcodes",
                    "size": len(self.upload_bytes),
                    "permissions": "rw",
                },
                "print_started": False,
                "print_queued": False,
                "action": "create_file",
            },
            status=201,
        )

    async def _start_print(self, request: web.Request) -> web.Response:
        self._check_auth(request)
        self.started_filename = request.query.get("filename")
        if self.start_delay:
            await asyncio.sleep(self.start_delay)
        return web.json_response("ok")


def test_settings_require_absolute_http_url() -> None:
    with pytest.raises(ValueError):
        MoonrakerHttpSettings("moonraker.local")


def test_connect_subscribes_and_streams_status_updates() -> None:
    async def scenario() -> None:
        server = _MoonrakerTestServer(api_key="secret", send_update=True)
        await server.start()
        transport = MoonrakerHttpTransport(MoonrakerHttpSettings(server.base_url, api_key="secret"))
        try:
            await transport.connect()
            initial = transport.snapshot()
            assert initial.connected is True
            assert initial.klippy_state == "ready"
            assert initial.print_state == "standby"
            assert server.subscription is not None
            assert server.subscription["method"] == "printer.objects.subscribe"

            events = transport.events()
            update = await asyncio.wait_for(anext(events), timeout=0.5)
            assert update.print_state == "printing"
            assert update.filename == "job.gcode"
            assert update.progress == 0.2
            assert update.print_duration_seconds == 3.5
        finally:
            await transport.disconnect()
            await server.close()

    asyncio.run(scenario())


def test_submit_uploads_checksum_then_starts_print(tmp_path: Path) -> None:
    async def scenario() -> None:
        server = _MoonrakerTestServer()
        await server.start()
        transport = MoonrakerHttpTransport(MoonrakerHttpSettings(server.base_url))
        payload = b"; FoxForge network test\nG28\n"
        path = tmp_path / "network.gcode"
        path.write_bytes(payload)
        digest = sha256(payload).hexdigest()
        try:
            await transport.connect()
            receipt = await transport.submit_print(
                MoonrakerNativePrintRequest(local_path=path.resolve(), filename=path.name, sha256=digest)
            )

            assert server.upload_filename == path.name
            assert server.upload_bytes == payload
            assert server.upload_fields == {"root": "gcodes", "checksum": digest, "print": "false"}
            assert server.started_filename == path.name
            assert receipt.vendor_job_id == path.name
        finally:
            await transport.disconnect()
            await server.close()

    asyncio.run(scenario())


def test_start_timeout_is_indeterminate_after_successful_upload(tmp_path: Path) -> None:
    async def scenario() -> None:
        server = _MoonrakerTestServer(start_delay=0.3)
        await server.start()
        transport = MoonrakerHttpTransport(MoonrakerHttpSettings(server.base_url, request_timeout_seconds=0.1))
        payload = b"G28\n"
        path = tmp_path / "timeout.gcode"
        path.write_bytes(payload)
        try:
            await transport.connect()
            with pytest.raises(MoonrakerTransportError) as caught:
                await transport.submit_print(
                    MoonrakerNativePrintRequest(
                        local_path=path.resolve(),
                        filename=path.name,
                        sha256=sha256(payload).hexdigest(),
                    )
                )
            assert caught.value.kind == MoonrakerTransportErrorKind.INDETERMINATE
            assert server.upload_filename == path.name
            assert server.started_filename == path.name
        finally:
            await transport.disconnect()
            await server.close()

    asyncio.run(scenario())
