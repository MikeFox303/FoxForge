# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

from aiohttp.test_utils import TestClient, TestServer

from foxforge.runtime import RuntimeSettings, create_runtime_app


def test_runtime_starts_empty_serves_api_and_spa_and_creates_durable_state(tmp_path) -> None:
    async def scenario() -> None:
        data_dir = tmp_path / "data"
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<html><body>FoxForge alpha</body></html>", encoding="utf-8")

        app = create_runtime_app(
            RuntimeSettings(
                data_dir=data_dir,
                config_path=data_dir / "config.json",
                static_dir=static_dir,
                reconnect_seconds=0.01,
            )
        )
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            health = await client.get("/healthz")
            assert health.status == 200
            assert (await health.json())["status"] == "ok"

            fleet = await client.get("/api/v1/fleet")
            assert fleet.status == 200
            assert await fleet.json() == {"apiVersion": "1", "printers": []}

            queue = await client.get("/api/v1/queue")
            assert queue.status == 200
            assert await queue.json() == {"apiVersion": "1", "entries": []}

            inventory = await client.get("/api/v1/inventory/spools")
            assert inventory.status == 200
            assert await inventory.json() == {"apiVersion": "1", "spools": []}

            root = await client.get("/")
            assert root.status == 200
            assert "FoxForge alpha" in await root.text()

            nested_route = await client.get("/printers/example")
            assert nested_route.status == 200
            assert "FoxForge alpha" in await nested_route.text()

            missing_api = await client.get("/api/v1/does-not-exist")
            assert missing_api.status == 404
            assert await missing_api.json() == {"error": "not_found"}
        finally:
            await client.close()

        assert (data_dir / "config.json").is_file()
        assert (data_dir / "foxforge.sqlite3").is_file()

    asyncio.run(scenario())


def test_runtime_without_frontend_remains_api_usable(tmp_path) -> None:
    async def scenario() -> None:
        data_dir = tmp_path / "data"
        app = create_runtime_app(
            RuntimeSettings(
                data_dir=data_dir,
                config_path=data_dir / "config.json",
                static_dir=None,
                reconnect_seconds=0.01,
            )
        )
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            root = await client.get("/")
            assert root.status == 200
            assert (await root.json())["status"] == "api-only"

            health = await client.get("/healthz")
            assert health.status == 200
        finally:
            await client.close()

    asyncio.run(scenario())
