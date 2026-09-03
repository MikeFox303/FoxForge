# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from decimal import Decimal

from aiohttp.test_utils import TestClient, TestServer

from foxforge.api import create_api_v1_app
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueService
from foxforge.domain.inventory import SpoolColor
from foxforge.testing import build_fake_printer
from tests.helpers import make_artifact


def test_read_only_api_v1_exposes_normalized_fleet_queue_and_inventory(
    tmp_path,
    printer_identity,
    material_snapshot,
) -> None:
    async def scenario() -> None:
        adapter, _, _ = build_fake_printer(
            printer_identity,
            material_snapshot=material_snapshot,
        )
        await adapter.connect()
        fleet = FleetService([adapter])
        queue = QueueService(fleet, InMemoryQueueStore())
        queue_entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "job.gcode"),
            requested_name="API test print",
        )

        inventory = InventoryService(InMemoryInventoryStore())
        spool = inventory.add_spool(
            material_family="PETG",
            initial_filament_mass_g=Decimal("1000"),
            manufacturer="SUNLU",
            product_name="PETG",
            color=SpoolColor("FF6600FF"),
            empty_spool_mass_g=Decimal("184.7"),
        )
        inventory.consume(
            spool.spool_id,
            Decimal("14.5"),
            idempotency_key="queue:completed:api-test",
        )
        inventory.assign_spool(
            spool.spool_id,
            printer_identity.printer_id,
            "opaque:unit-a:slot-0",
        )

        app = create_api_v1_app(fleet=fleet, queue=queue, inventory=inventory)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            health = await client.get("/healthz")
            assert health.status == 200
            assert await health.json() == {"status": "ok", "apiVersion": "1"}
            assert health.headers["Cache-Control"] == "no-store"
            assert health.headers["X-FoxForge-Api-Version"] == "1"

            fleet_response = await client.get("/api/v1/fleet")
            assert fleet_response.status == 200
            fleet_payload = await fleet_response.json()
            assert fleet_payload["apiVersion"] == "1"
            assert len(fleet_payload["printers"]) == 1
            printer = fleet_payload["printers"][0]
            assert printer["identity"]["printerId"] == printer_identity.printer_id
            assert printer["snapshot"]["connection"] == "connected"
            assert printer["snapshot"]["operationalState"] == "idle"
            capability_ids = {item["capabilityId"] for item in printer["capabilities"]}
            assert capability_ids == {"foxforge.print_execution", "foxforge.material_system"}
            assert printer["materialSystem"]["units"][0]["kind"] == "multi_slot"
            first_slot = printer["materialSystem"]["units"][0]["slots"][0]
            assert first_slot["slotId"] == "opaque:unit-a:slot-0"
            assert first_slot["detectedMaterial"]["materialFamily"] == "PETG"

            queue_response = await client.get("/api/v1/queue")
            assert queue_response.status == 200
            queue_payload = await queue_response.json()
            assert queue_payload["apiVersion"] == "1"
            entry = queue_payload["entries"][0]
            assert entry["queueId"] == str(queue_entry.queue_id)
            assert entry["state"] == "pending"
            assert entry["request"]["requestedName"] == "API test print"
            artifact = entry["request"]["artifact"]
            assert artifact["filename"] == "job.gcode"
            assert "path" not in artifact

            inventory_response = await client.get("/api/v1/inventory/spools")
            assert inventory_response.status == 200
            inventory_payload = await inventory_response.json()
            assert inventory_payload["apiVersion"] == "1"
            spool_payload = inventory_payload["spools"][0]
            assert spool_payload["spoolId"] == str(spool.spool_id)
            assert spool_payload["initialFilamentMassG"] == "1000"
            assert spool_payload["remainingFilamentMassG"] == "985.5"
            assert spool_payload["usedFilamentMassG"] == "14.5"
            assert spool_payload["emptySpoolMassG"] == "184.7"
            assert spool_payload["assignment"] == {
                "printerId": printer_identity.printer_id,
                "slotId": "opaque:unit-a:slot-0",
                "assignedAt": spool_payload["assignment"]["assignedAt"],
            }
        finally:
            await client.close()
            await queue.aclose()
            await fleet.aclose()

    asyncio.run(scenario())


def test_api_v1_queue_uses_full_backend_lifecycle_state(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, _, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        fleet = FleetService([adapter])
        queue = QueueService(fleet, InMemoryQueueStore())
        entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "lifecycle.gcode"),
        )
        accepted = await queue.dispatch(entry.queue_id)
        assert accepted.state.value == "accepted"

        app = create_api_v1_app(
            fleet=fleet,
            queue=queue,
            inventory=InventoryService(InMemoryInventoryStore()),
        )
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/api/v1/queue")
            payload = await response.json()
            assert payload["entries"][0]["state"] == "accepted"
            assert payload["entries"][0]["receipt"]["vendorJobId"] is not None
        finally:
            await client.close()
            await queue.aclose()
            await fleet.aclose()

    asyncio.run(scenario())
