# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

from aiohttp.test_utils import TestClient, TestServer

from foxforge.api import create_api_v1_app
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueService
from foxforge.domain.printers import utc_now
from foxforge.domain.printers.capabilities import (
    MaterialRouteKind,
    MaterialRouteSnapshot,
    MaterialToolheadSnapshot,
    MaterialTopologySnapshot,
)
from foxforge.testing import build_fake_printer


def test_fleet_api_exposes_optional_material_topology(printer_identity) -> None:
    async def scenario() -> None:
        topology = MaterialTopologySnapshot(
            printer_id=printer_identity.printer_id,
            toolheads=(
                MaterialToolheadSnapshot(toolhead_id="tool-right", label="Right", position=0),
                MaterialToolheadSnapshot(toolhead_id="tool-left", label="Left", position=1),
            ),
            routes=(
                MaterialRouteSnapshot(
                    source_slot_id="opaque:external:right",
                    toolhead_ids=("tool-right",),
                    kind=MaterialRouteKind.FIXED,
                ),
                MaterialRouteSnapshot(
                    source_slot_id="opaque:external:left",
                    toolhead_ids=("tool-left",),
                    kind=MaterialRouteKind.FIXED,
                ),
            ),
            observed_at=utc_now(),
            stale=False,
        )
        adapter, _, _ = build_fake_printer(
            printer_identity,
            material_topology_snapshot=topology,
        )
        await adapter.connect()
        fleet = FleetService([adapter])
        queue = QueueService(fleet, InMemoryQueueStore())
        app = create_api_v1_app(
            fleet=fleet,
            queue=queue,
            inventory=InventoryService(InMemoryInventoryStore()),
        )
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/api/v1/fleet")
            assert response.status == 200
            printer = (await response.json())["printers"][0]

            topology_capability = next(
                item for item in printer["capabilities"] if item["capabilityId"] == "foxforge.material_topology"
            )
            assert topology_capability == {
                "capabilityId": "foxforge.material_topology",
                "majorVersion": 1,
                "reportsDynamicRoutes": False,
            }
            assert printer["materialTopology"]["printerId"] == printer_identity.printer_id
            assert printer["materialTopology"]["toolheads"] == [
                {"toolheadId": "tool-right", "label": "Right", "position": 0},
                {"toolheadId": "tool-left", "label": "Left", "position": 1},
            ]
            assert printer["materialTopology"]["routes"] == [
                {
                    "sourceSlotId": "opaque:external:right",
                    "toolheadIds": ["tool-right"],
                    "kind": "fixed",
                },
                {
                    "sourceSlotId": "opaque:external:left",
                    "toolheadIds": ["tool-left"],
                    "kind": "fixed",
                },
            ]
        finally:
            await client.close()
            await queue.aclose()
            await fleet.aclose()

    asyncio.run(scenario())
