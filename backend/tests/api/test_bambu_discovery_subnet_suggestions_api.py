# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1 import BearerCommandSecurity, create_api_v1_app
from foxforge.application.commands import InMemoryCommandIdempotencyStore
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueService
from foxforge.runtime.bambu_discovery_routes import register_bambu_discovery_routes

_TOKEN = "test-bambu-subnet-suggestion-token-0123456789"


def _app(suggester):
    fleet = FleetService()
    app = create_api_v1_app(
        fleet=fleet,
        queue=QueueService(fleet, InMemoryQueueStore()),
        inventory=InventoryService(InMemoryInventoryStore()),
        command_security=BearerCommandSecurity(_TOKEN),
        command_idempotency=InMemoryCommandIdempotencyStore(),
    )
    register_bambu_discovery_routes(app, subnet_suggester=suggester)
    return app


def test_subnet_suggestions_require_operator_auth_before_enumeration() -> None:
    async def scenario() -> None:
        calls = 0

        def suggester() -> tuple[str, ...]:
            nonlocal calls
            calls += 1
            return ("192.168.50.0/24",)

        client = TestClient(TestServer(_app(suggester)))
        await client.start_server()
        try:
            unauthorized = await client.get("/api/v1/printers/discovery/bambu/subnets")
            assert unauthorized.status == 401
            assert calls == 0

            response = await client.get(
                "/api/v1/printers/discovery/bambu/subnets",
                headers={"Authorization": f"Bearer {_TOKEN}"},
            )
            assert response.status == 200
            assert calls == 1
            assert await response.json() == {
                "apiVersion": "1",
                "subnets": ["192.168.50.0/24"],
            }
        finally:
            await client.close()

    asyncio.run(scenario())


def test_subnet_suggestion_enumeration_failure_is_safe_empty_read() -> None:
    async def scenario() -> None:
        def suggester() -> tuple[str, ...]:
            raise OSError("interface enumeration unavailable")

        client = TestClient(TestServer(_app(suggester)))
        await client.start_server()
        try:
            response = await client.get(
                "/api/v1/printers/discovery/bambu/subnets",
                headers={"Authorization": f"Bearer {_TOKEN}"},
            )
            assert response.status == 200
            assert await response.json() == {"apiVersion": "1", "subnets": []}
        finally:
            await client.close()

    asyncio.run(scenario())
