# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1 import BearerCommandSecurity, create_api_v1_app
from foxforge.api.v1.command_audit import install_command_audit
from foxforge.api.v1.filament_accounting import register_filament_accounting_routes
from foxforge.application.accounting import (
    FilamentAccountingService,
    FilamentReservationState,
    InMemoryFilamentAccountingStore,
    MaterialEstimate,
)
from foxforge.application.commands import (
    CommandAuditOutcome,
    InMemoryCommandAuditStore,
    InMemoryCommandIdempotencyStore,
)
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueEntryState, QueueService
from foxforge.domain.printers import PrinterIdentity
from foxforge.domain.printers.capabilities import MaterialBinding, PrintDispatchReceipt
from foxforge.testing import build_fake_printer
from tests.helpers import make_artifact

_TOKEN = "filament-accounting-token-0123456789abcdef"
_PRINTER_ID = "printer-1"
_SLOT_ID = "slot-0"


def _headers(key: str, request_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_TOKEN}",
        "Idempotency-Key": key,
        "X-Request-Id": request_id,
    }


def _build_app():
    identity = PrinterIdentity(
        printer_id=_PRINTER_ID,
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
    idempotency = InMemoryCommandIdempotencyStore()
    audit = InMemoryCommandAuditStore()
    security = BearerCommandSecurity(_TOKEN)
    app = create_api_v1_app(
        fleet=fleet,
        queue=queue,
        inventory=inventory,
        command_security=security,
        command_idempotency=idempotency,
    )
    register_filament_accounting_routes(
        app,
        queue=queue,
        inventory=inventory,
        accounting=accounting,
    )
    install_command_audit(app, security=security, store=audit)
    return app, fleet, queue, inventory, accounting, idempotency, audit


def _enqueue(queue: QueueService, tmp_path, *, filename: str = "accounting.gcode"):
    return queue.enqueue(
        _PRINTER_ID,
        make_artifact(tmp_path / filename),
        material_bindings=(MaterialBinding(0, _SLOT_ID),),
    )


def _assign_spool(inventory: InventoryService, *, mass: str = "100"):
    spool = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal(mass))
    inventory.assign_spool(spool.spool_id, _PRINTER_ID, _SLOT_ID)
    return spool


def _receipt(entry) -> PrintDispatchReceipt:
    return PrintDispatchReceipt(
        dispatch_id=entry.request.dispatch_id,
        accepted_at=datetime.now(UTC),
        vendor_job_id="vendor-job-1",
        artifact_sha256=entry.request.artifact.sha256,
    )


def test_plan_requires_auth_and_is_exact_idempotent_and_audited(tmp_path) -> None:
    async def scenario() -> None:
        app, fleet, queue, inventory, accounting, _, audit = _build_app()
        spool = _assign_spool(inventory)
        entry = _enqueue(queue, tmp_path)
        client = TestClient(TestServer(app))
        await client.start_server()
        payload = {"estimates": [{"materialIndex": 0, "estimatedMassG": "25.50"}]}
        try:
            denied = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-plan",
                json=payload,
                headers={"Idempotency-Key": "plan-denied", "X-Request-Id": "req-plan-denied"},
            )
            assert denied.status == 401
            assert accounting.reservations_for_queue(entry.queue_id) == ()

            planned = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-plan",
                json=payload,
                headers=_headers("plan-1", "req-plan-1"),
            )
            assert planned.status == 201
            body = await planned.json()
            assert body["replayed"] is False
            assert body["reservations"][0]["estimatedMassG"] == "25.50"
            assert body["reservations"][0]["spoolId"] == str(spool.spool_id)
            assert accounting.available_mass(spool.spool_id) == Decimal("74.50")
            assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")

            replay = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-plan",
                json=payload,
                headers=_headers("plan-1", "req-plan-replay"),
            )
            assert replay.status == 200
            assert (await replay.json())["replayed"] is True
            assert len(accounting.reservations_for_queue(entry.queue_id)) == 1

            snapshot = await client.get("/api/v1/filament-accounting")
            assert snapshot.status == 200
            snapshot_body = await snapshot.json()
            assert snapshot_body["reservations"][0]["queueId"] == str(entry.queue_id)
            assert snapshot_body["spools"] == [
                {
                    "spoolId": str(spool.spool_id),
                    "reservedMassG": "25.50",
                    "availableMassG": "74.50",
                }
            ]

            records = audit.list_for_request("req-plan-1")
            assert [record.outcome for record in records] == [
                CommandAuditOutcome.ACCEPTED,
                CommandAuditOutcome.COMPLETED,
            ]
            assert records[0].action == "filament.plan"
            assert records[0].target_ref == str(entry.queue_id)
        finally:
            await queue.aclose()
            await fleet.aclose()
            await client.close()

    asyncio.run(scenario())


def test_predictable_plan_conflict_does_not_reserve_command_key(tmp_path) -> None:
    async def scenario() -> None:
        app, fleet, queue, inventory, _, idempotency, _ = _build_app()
        _assign_spool(inventory, mass="10")
        entry = _enqueue(queue, tmp_path, filename="capacity.gcode")
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-plan",
                json={"estimates": [{"materialIndex": 0, "estimatedMassG": "11"}]},
                headers=_headers("capacity-key", "req-capacity"),
            )
            assert response.status == 409
            assert (await response.json())["error"]["code"] == "insufficient_filament"
            assert idempotency.get("operator", "filament.plan", "capacity-key") is None
        finally:
            await queue.aclose()
            await fleet.aclose()
            await client.close()

    asyncio.run(scenario())


def test_release_is_prestart_only_and_terminal_plan_cannot_be_recreated(tmp_path) -> None:
    async def scenario() -> None:
        app, fleet, queue, inventory, accounting, idempotency, _ = _build_app()
        spool = _assign_spool(inventory)
        entry = _enqueue(queue, tmp_path, filename="release.gcode")
        client = TestClient(TestServer(app))
        await client.start_server()
        plan_payload = {"estimates": [{"materialIndex": 0, "estimatedMassG": "20"}]}
        try:
            planned = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-plan",
                json=plan_payload,
                headers=_headers("release-plan", "req-release-plan"),
            )
            assert planned.status == 201

            released = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-release",
                headers=_headers("release-1", "req-release-1"),
            )
            assert released.status == 200
            reservation = accounting.reservations_for_queue(entry.queue_id)[0]
            assert reservation.state == FilamentReservationState.RELEASED
            assert accounting.reserved_mass(spool.spool_id) == Decimal("0")

            rejected = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-plan",
                json=plan_payload,
                headers=_headers("replan-terminal", "req-replan-terminal"),
            )
            assert rejected.status == 409
            assert (await rejected.json())["error"]["code"] == "filament_plan_conflict"
            assert idempotency.get("operator", "filament.plan", "replan-terminal") is None
        finally:
            await queue.aclose()
            await fleet.aclose()
            await client.close()

    asyncio.run(scenario())


def test_reconciliation_is_exact_idempotent_and_preflight_conflicts_do_not_stick(tmp_path) -> None:
    async def scenario() -> None:
        app, fleet, queue, inventory, accounting, idempotency, _ = _build_app()
        spool = _assign_spool(inventory)
        entry = _enqueue(queue, tmp_path, filename="reconcile.gcode")
        accounting.plan(entry, (MaterialEstimate(0, Decimal("30")),))
        accounting.sync_queue_entry(
            replace(
                entry,
                state=QueueEntryState.CANCELLED,
                receipt=_receipt(entry),
                updated_at=datetime.now(UTC),
            )
        )

        client = TestClient(TestServer(app))
        await client.start_server()
        payload = {
            "materialIndex": 0,
            "actualMassG": "12.50",
            "note": "weighed after cancellation",
        }
        try:
            reconciled = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-reconcile",
                json=payload,
                headers=_headers("reconcile-1", "req-reconcile-1"),
            )
            assert reconciled.status == 200
            reservation = accounting.reservations_for_queue(entry.queue_id)[0]
            assert reservation.state == FilamentReservationState.CONSUMED
            assert reservation.actual_mass_g == Decimal("12.50")
            assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("87.50")

            replay = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-reconcile",
                json=payload,
                headers=_headers("reconcile-1", "req-reconcile-replay"),
            )
            assert replay.status == 200
            assert (await replay.json())["replayed"] is True
            assert len(inventory.adjustments(spool.spool_id)) == 1

            conflict = await client.post(
                f"/api/v1/queue/{entry.queue_id}/filament-reconcile",
                json={"materialIndex": 0, "actualMassG": "13"},
                headers=_headers("reconcile-conflict", "req-reconcile-conflict"),
            )
            assert conflict.status == 409
            assert (await conflict.json())["error"]["code"] == "filament_reconciliation_conflict"
            assert idempotency.get("operator", "filament.reconcile", "reconcile-conflict") is None
        finally:
            await queue.aclose()
            await fleet.aclose()
            await client.close()

    asyncio.run(scenario())
