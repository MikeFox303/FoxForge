# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

from aiohttp.test_utils import TestClient, TestServer

from foxforge.adapters.bambu import BambuDiscoveryCandidate
from foxforge.api.v1 import BearerCommandSecurity, create_api_v1_app
from foxforge.api.v1.bambu_discovery import register_bambu_discovery_routes
from foxforge.application.commands import InMemoryCommandIdempotencyStore
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueService

_TOKEN = "test-bambu-discovery-token-0123456789"


def _app(scanner):
    fleet = FleetService()
    app = create_api_v1_app(
        fleet=fleet,
        queue=QueueService(fleet, InMemoryQueueStore()),
        inventory=InventoryService(InMemoryInventoryStore()),
        command_security=BearerCommandSecurity(_TOKEN),
        command_idempotency=InMemoryCommandIdempotencyStore(),
    )
    register_bambu_discovery_routes(app, scanner=scanner)
    return app


def test_bambu_discovery_requires_operator_auth_and_returns_candidates_only() -> None:
    async def scenario() -> None:
        calls: list[str] = []

        async def scanner(subnet: str) -> tuple[BambuDiscoveryCandidate, ...]:
            calls.append(subnet)
            return (
                BambuDiscoveryCandidate(
                    host="192.168.50.151",
                    serial_number="01P00X2D",
                    display_name="X2D",
                    model="X2D",
                ),
            )

        client = TestClient(TestServer(_app(scanner)))
        await client.start_server()
        try:
            unauthorized = await client.post(
                "/api/v1/printers/discovery/bambu",
                json={"subnet": "192.168.50.0/24"},
            )
            assert unauthorized.status == 401
            assert calls == []

            response = await client.post(
                "/api/v1/printers/discovery/bambu",
                json={"subnet": "192.168.50.0/24"},
                headers={"Authorization": f"Bearer {_TOKEN}"},
            )
            assert response.status == 200
            body = await response.json()
            assert calls == ["192.168.50.0/24"]
            assert body == {
                "apiVersion": "1",
                "candidates": [
                    {
                        "host": "192.168.50.151",
                        "serialNumber": "01P00X2D",
                        "displayName": "X2D",
                        "model": "X2D",
                        "services": {"mqttPort": 8883, "ftpsPort": 990},
                    }
                ],
            }
            assert "accessCode" not in str(body)
        finally:
            await client.close()

    asyncio.run(scenario())


def test_bambu_discovery_rejects_invalid_payload_before_scanning() -> None:
    async def scenario() -> None:
        calls: list[str] = []

        async def scanner(subnet: str) -> tuple[BambuDiscoveryCandidate, ...]:
            calls.append(subnet)
            return ()

        client = TestClient(TestServer(_app(scanner)))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/printers/discovery/bambu",
                json={"subnet": "", "accessCode": "must-not-be-accepted"},
                headers={"Authorization": f"Bearer {_TOKEN}"},
            )
            assert response.status == 400
            body = await response.json()
            assert body["error"]["code"] == "invalid_request"
            assert calls == []
            assert "must-not-be-accepted" not in str(body)
        finally:
            await client.close()

    asyncio.run(scenario())


def test_bambu_discovery_requires_json_media_type() -> None:
    async def scenario() -> None:
        async def scanner(subnet: str) -> tuple[BambuDiscoveryCandidate, ...]:
            raise AssertionError("scanner must not run")

        client = TestClient(TestServer(_app(scanner)))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/printers/discovery/bambu",
                data="subnet=192.168.1.0/24",
                headers={"Authorization": f"Bearer {_TOKEN}", "Content-Type": "text/plain"},
            )
            assert response.status == 415
            assert (await response.json())["error"]["code"] == "unsupported_media_type"
        finally:
            await client.close()

    asyncio.run(scenario())
