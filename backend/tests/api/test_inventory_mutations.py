# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from uuid import UUID

from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1 import BearerCommandSecurity, create_api_v1_app
from foxforge.api.v1.inventory_commands import register_inventory_command_routes
from foxforge.application.commands import InMemoryCommandIdempotencyStore
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueService
from foxforge.domain.printers import PrinterIdentity, utc_now
from foxforge.domain.printers.capabilities import (
    MaterialActivity,
    MaterialPresence,
    MaterialSlotSnapshot,
    MaterialSystemSnapshot,
    MaterialUnitKind,
    MaterialUnitSnapshot,
)
from foxforge.testing import build_fake_printer

_TOKEN = "inventory-command-token-0123456789abcdef"
_SPOOL_ID = "20fdc5cb-7af3-4c3d-8f50-a97ff26c02f5"


def _headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_TOKEN}",
        "Idempotency-Key": key,
    }


def _app() -> tuple[object, InventoryService]:
    identity = PrinterIdentity(
        printer_id="x2d-main",
        display_name="Bambu X2D",
        vendor="bambu_lab",
        model="X2D",
        serial_number="SERIAL",
        adapter_kind="fake",
    )
    unit_id = "bambu:unit:0"
    material = MaterialSystemSnapshot(
        printer_id=identity.printer_id,
        units=(
            MaterialUnitSnapshot(
                unit_id=unit_id,
                kind=MaterialUnitKind.MULTI_SLOT,
                label="AMS 2 Pro",
                position=0,
                slots=(
                    MaterialSlotSnapshot(
                        slot_id="bambu:unit:0:tray:0",
                        unit_id=unit_id,
                        position=0,
                        label="A1",
                        presence=MaterialPresence.LOADED,
                        activity=MaterialActivity.INACTIVE,
                        detected_material=None,
                    ),
                    MaterialSlotSnapshot(
                        slot_id="bambu:unit:0:tray:1",
                        unit_id=unit_id,
                        position=1,
                        label="A2",
                        presence=MaterialPresence.EMPTY,
                        activity=MaterialActivity.INACTIVE,
                        detected_material=None,
                    ),
                ),
            ),
        ),
        observed_at=utc_now(),
        stale=False,
    )
    adapter, _, _ = build_fake_printer(identity, material_snapshot=material)
    fleet = FleetService([adapter])
    inventory = InventoryService(InMemoryInventoryStore())
    app = create_api_v1_app(
        fleet=fleet,
        queue=QueueService(fleet, InMemoryQueueStore()),
        inventory=inventory,
        command_security=BearerCommandSecurity(_TOKEN),
        command_idempotency=InMemoryCommandIdempotencyStore(),
    )
    register_inventory_command_routes(app, inventory=inventory, fleet=fleet)
    return app, inventory


def test_inventory_mutation_lifecycle_is_authenticated_idempotent_and_live_readable() -> None:
    async def scenario() -> None:
        app, inventory = _app()
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            add_payload = {
                "spoolId": _SPOOL_ID,
                "materialFamily": "PETG",
                "manufacturer": "SUNLU",
                "productName": "PETG",
                "rgbaHex": "#FF6600",
                "initialFilamentMassG": "1000",
                "emptySpoolMassG": "180",
                "purchaseDate": "2026-09-04",
            }
            added = await client.post("/api/v1/inventory/spools", json=add_payload, headers=_headers("add-1"))
            assert added.status == 201
            assert (await added.json())["remainingFilamentMassG"] == "1000"

            replay = await client.post("/api/v1/inventory/spools", json=add_payload, headers=_headers("add-1"))
            assert replay.status == 200
            assert (await replay.json())["replayed"] is True
            assert len(inventory.list_spools(include_archived=True)) == 1

            corrected = await client.post(
                f"/api/v1/inventory/spools/{_SPOOL_ID}/correct-remaining",
                json={"remainingFilamentMassG": "735.5", "note": "scale correction"},
                headers=_headers("correct-1"),
            )
            assert corrected.status == 200
            assert (await corrected.json())["remainingFilamentMassG"] == "735.5"

            moved = await client.put(
                f"/api/v1/inventory/spools/{_SPOOL_ID}/assignment",
                json={"printerId": "x2d-main", "slotId": "bambu:unit:0:tray:0"},
                headers=_headers("move-1"),
            )
            assert moved.status == 200
            assert (await moved.json())["slotId"] == "bambu:unit:0:tray:0"

            moved_again = await client.put(
                f"/api/v1/inventory/spools/{_SPOOL_ID}/assignment",
                json={"printerId": "x2d-main", "slotId": "bambu:unit:0:tray:1"},
                headers=_headers("move-2"),
            )
            assert moved_again.status == 200
            assert inventory.assignment_for_spool(UUID(_SPOOL_ID)).slot_id == "bambu:unit:0:tray:1"

            unassigned = await client.delete(
                f"/api/v1/inventory/spools/{_SPOOL_ID}/assignment",
                headers=_headers("unassign-1"),
            )
            assert unassigned.status == 200
            assert inventory.assignment_for_spool(UUID(_SPOOL_ID)) is None

            archived = await client.post(
                f"/api/v1/inventory/spools/{_SPOOL_ID}/archive",
                headers=_headers("archive-1"),
            )
            assert archived.status == 200
            assert (await archived.json())["archived"] is True

            read = await client.get("/api/v1/inventory/spools")
            assert read.status == 200
            payload = await read.json()
            assert payload["spools"][0]["remainingFilamentMassG"] == "735.5"
            assert payload["spools"][0]["archived"] is True
        finally:
            await client.close()

    asyncio.run(scenario())


def test_inventory_mutations_fail_closed_without_credentials_and_reject_changed_replay() -> None:
    async def scenario() -> None:
        app, _ = _app()
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            payload = {
                "spoolId": _SPOOL_ID,
                "materialFamily": "PLA",
                "initialFilamentMassG": "1000",
            }
            unauthorized = await client.post("/api/v1/inventory/spools", json=payload, headers={"Idempotency-Key": "same"})
            assert unauthorized.status == 401

            first = await client.post("/api/v1/inventory/spools", json=payload, headers=_headers("same"))
            assert first.status == 201

            changed = dict(payload)
            changed["materialFamily"] = "PETG"
            conflict = await client.post("/api/v1/inventory/spools", json=changed, headers=_headers("same"))
            assert conflict.status == 409
            assert (await conflict.json())["error"]["code"] == "idempotency_conflict"
        finally:
            await client.close()

    asyncio.run(scenario())
