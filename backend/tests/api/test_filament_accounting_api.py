# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1 import BearerCommandSecurity, create_api_v1_app
from foxforge.api.v1.filament_accounting import register_filament_accounting_routes
from foxforge.application.accounting import FilamentAccountingService, InMemoryFilamentAccountingStore
from foxforge.application.commands import InMemoryCommandIdempotencyStore
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueService
from foxforge.domain.printers import PrinterIdentity
from foxforge.domain.printers.capabilities import (
    LocalPrintArtifact,
    MaterialBinding,
    PrintArtifactFormat,
)
from foxforge.testing import build_fake_printer

_TOKEN = "filament-accounting-token-0123456789abcdef"


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_TOKEN}", "Idempotency-Key": key}


def _app() -> tuple[web.Application, QueueService, InventoryService, FilamentAccountingService]:
    identity = PrinterIdentity(
        printer_id="printer-1",
        display_name="Printer 1",
        vendor="test",
        model="Test",
        serial_number=None,
        adapter_kind="fake",
    )
    adapter, _, _ = build_fake_printer(identity)
    fleet = FleetService([adapter])
    queue = QueueService(fleet, InMemoryQueueStore())
    inventory = InventoryService(InMemoryInventoryStore())
    accounting = FilamentAccountingService(inventory, InMemoryFilamentAccountingStore())
    app = create_api_v1_app(
        fleet=fleet,
        queue=queue,
        inventory=inventory,
        command_security=BearerCommandSecurity(_TOKEN),
        command_idempotency=InMemoryCommandIdempotencyStore(),
    )
    register_filament_accounting_routes(app, queue=queue, accounting=accounting)
    return app, queue, inventory, accounting


def test_filament_plan_is_authenticated_exact_decimal_and_idempotent() -> None:
    async def scenario() -> None:
        app, queue, inventory, accounting = _app()
        spool = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("100"))
        inventory.assign_spool(spool.spool_id, "printer-1", "slot-0")
        entry = queue.enqueue(
            "printer-1",
            LocalPrintArtifact(
                artifact_id="a" * 64,
                path=Path("/data/artifacts/job.gcode"),
                filename="job.gcode",
                format=PrintArtifactFormat.GCODE,
                size_bytes=10,
                sha256="a" * 64,
            ),
            material_bindings=(MaterialBinding(material_index=0, slot_id="slot-0"),),
        )
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            payload = {"estimates": [{"materialIndex": 0, "estimatedMassG": "25.5"}]}
            planned = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-plan",
                json=payload,
                headers=_headers("plan-1"),
            )
            assert planned.status == 201
            body = await planned.json()
            assert body["reservations"][0]["estimatedMassG"] == "25.5"
            assert body["reservations"][0]["spoolId"] == str(spool.spool_id)
            assert accounting.available_mass(spool.spool_id) == Decimal("74.5")

            replay = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-plan",
                json=payload,
                headers=_headers("plan-1"),
            )
            assert replay.status == 200
            assert (await replay.json())["replayed"] is True
            assert len(accounting.reservations_for_queue(entry.queue_id)) == 1

            conflict = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-plan",
                json={"estimates": [{"materialIndex": 0, "estimatedMassG": "26"}]},
                headers=_headers("plan-2"),
            )
            assert conflict.status == 409

            snapshot = await client.get("/api/v1/filament-accounting")
            assert snapshot.status == 200
            snapshot_body = await snapshot.json()
            assert snapshot_body["spools"][0]["reservedMassG"] == "25.5"
            assert snapshot_body["spools"][0]["availableMassG"] == "74.5"
        finally:
            await client.close()

    asyncio.run(scenario())
