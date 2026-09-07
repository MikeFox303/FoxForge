# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace
from decimal import Decimal

from foxforge.application.accounting import (
    FilamentAccountingQueuePolicy,
    FilamentAccountingService,
    FilamentReservationState,
    InMemoryFilamentAccountingStore,
    MaterialEstimate,
)
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueEntryState, QueueService
from foxforge.domain.printers import (
    ActiveJobSnapshot,
    JobState,
    OperationalState,
    PrinterAdapterError,
    PrinterErrorCode,
    utc_now,
)
from foxforge.domain.printers.capabilities import (
    DetectedMaterial,
    MaterialActivity,
    MaterialBinding,
    MaterialPresence,
    MaterialSlotSnapshot,
    MaterialSystemSnapshot,
    MaterialUnitKind,
    MaterialUnitSnapshot,
    PrintAssessmentBlockerCode,
)
from foxforge.infrastructure.accounting import SQLiteFilamentAccountingStore
from foxforge.infrastructure.inventory import SQLiteInventoryStore
from foxforge.infrastructure.queue import SQLiteQueueStore
from foxforge.testing import build_fake_printer
from tests.helpers import make_artifact

_SLOT_ID = "source:slot-0"
_OTHER_SLOT_ID = "source:slot-1"


async def _wait_for_state(queue: QueueService, queue_id, state: QueueEntryState) -> None:
    for _ in range(100):
        if queue.get(queue_id).state == state:
            return
        await asyncio.sleep(0.005)
    assert queue.get(queue_id).state == state


def _material_snapshot(printer_id: str) -> MaterialSystemSnapshot:
    slot = MaterialSlotSnapshot(
        slot_id=_SLOT_ID,
        unit_id="source:unit-0",
        position=0,
        label="Source 1",
        presence=MaterialPresence.LOADED,
        activity=MaterialActivity.INACTIVE,
        detected_material=DetectedMaterial(
            material_family="PETG",
            vendor_name="Test",
            product_name="PETG",
            color=None,
            tag=None,
            remaining_fraction=0.8,
        ),
    )
    return MaterialSystemSnapshot(
        printer_id=printer_id,
        units=(
            MaterialUnitSnapshot(
                unit_id="source:unit-0",
                kind=MaterialUnitKind.MULTI_SLOT,
                label="Sources",
                position=0,
                slots=(slot,),
            ),
        ),
        observed_at=utc_now(),
        stale=False,
    )


def _accounting(printer_id: str, *, mass: str = "100"):
    inventory = InventoryService(InMemoryInventoryStore())
    spool = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal(mass))
    inventory.assign_spool(spool.spool_id, printer_id, _SLOT_ID)
    accounting = FilamentAccountingService(inventory, InMemoryFilamentAccountingStore())
    return inventory, accounting, spool


def _job(vendor_job_id: str, state: JobState) -> ActiveJobSnapshot:
    return ActiveJobSnapshot(
        vendor_job_id=vendor_job_id,
        name="accounted.gcode",
        state=state,
        progress=1.0 if state == JobState.COMPLETED else None,
        elapsed_seconds=None,
        remaining_seconds=None,
        current_layer=None,
        total_layers=None,
    )


def test_missing_accounting_plan_blocks_before_dispatch_boundary(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(
            printer_identity,
            material_snapshot=_material_snapshot(printer_identity.printer_id),
        )
        await adapter.connect()
        inventory, accounting, _ = _accounting(printer_identity.printer_id)
        policy = FilamentAccountingQueuePolicy(accounting, inventory)
        queue = QueueService(
            FleetService([adapter]),
            InMemoryQueueStore(),
            pre_dispatch_gate=policy,
            lifecycle_observer=policy,
        )
        entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "missing-plan.gcode"),
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )

        try:
            blocked = await queue.dispatch(entry.queue_id)
            assert blocked.state == QueueEntryState.BLOCKED
            assert blocked.attempt_count == 0
            assert blocked.assessment is not None
            assert blocked.assessment.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID
            assert printing.submit_attempt_count == 0
            assert printing.start_count == 0
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def test_valid_accounting_plan_allows_exactly_one_dispatch(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(
            printer_identity,
            material_snapshot=_material_snapshot(printer_identity.printer_id),
        )
        await adapter.connect()
        inventory, accounting, spool = _accounting(printer_identity.printer_id)
        policy = FilamentAccountingQueuePolicy(accounting, inventory)
        queue = QueueService(
            FleetService([adapter]),
            InMemoryQueueStore(),
            pre_dispatch_gate=policy,
            lifecycle_observer=policy,
        )
        entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "valid-plan.gcode"),
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )
        accounting.plan(entry, (MaterialEstimate(0, Decimal("20")),))

        try:
            accepted = await queue.dispatch(entry.queue_id)
            replay = await queue.dispatch(entry.queue_id)
            assert accepted.state == QueueEntryState.ACCEPTED
            assert replay == accepted
            assert accepted.attempt_count == 1
            assert printing.start_count == 1
            assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")
            reservation = accounting.reservations_for_queue(entry.queue_id)[0]
            assert reservation.state == FilamentReservationState.RESERVED
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def test_spool_assignment_drift_blocks_before_submit(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(
            printer_identity,
            material_snapshot=_material_snapshot(printer_identity.printer_id),
        )
        await adapter.connect()
        inventory, accounting, spool = _accounting(printer_identity.printer_id)
        policy = FilamentAccountingQueuePolicy(accounting, inventory)
        queue = QueueService(
            FleetService([adapter]),
            InMemoryQueueStore(),
            pre_dispatch_gate=policy,
            lifecycle_observer=policy,
        )
        entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "assignment-drift.gcode"),
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )
        accounting.plan(entry, (MaterialEstimate(0, Decimal("20")),))
        inventory.move_spool(spool.spool_id, printer_identity.printer_id, _OTHER_SLOT_ID)
        replacement = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal("100"))
        inventory.assign_spool(replacement.spool_id, printer_identity.printer_id, _SLOT_ID)

        try:
            blocked = await queue.dispatch(entry.queue_id)
            assert blocked.state == QueueEntryState.BLOCKED
            assert blocked.attempt_count == 0
            assert blocked.assessment is not None
            assert blocked.assessment.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE
            assert printing.submit_attempt_count == 0
            assert accounting.reservations_for_queue(entry.queue_id)[0].spool_id == spool.spool_id
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def test_capacity_drift_uses_full_active_hold_and_blocks(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(
            printer_identity,
            material_snapshot=_material_snapshot(printer_identity.printer_id),
        )
        await adapter.connect()
        inventory, accounting, spool = _accounting(printer_identity.printer_id)
        policy = FilamentAccountingQueuePolicy(accounting, inventory)
        queue = QueueService(
            FleetService([adapter]),
            InMemoryQueueStore(),
            pre_dispatch_gate=policy,
            lifecycle_observer=policy,
        )
        entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "capacity-drift.gcode"),
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )
        accounting.plan(entry, (MaterialEstimate(0, Decimal("80")),))
        inventory.consume(spool.spool_id, Decimal("30"), idempotency_key="manual:parallel-use")

        try:
            blocked = await queue.dispatch(entry.queue_id)
            assert blocked.state == QueueEntryState.BLOCKED
            assert blocked.attempt_count == 0
            assert blocked.assessment is not None
            assert blocked.assessment.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE
            assert printing.submit_attempt_count == 0
            assert accounting.reserved_mass(spool.spool_id) == Decimal("80")
            assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("70")
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def test_completion_event_settles_estimate_exactly_once(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, _, _ = build_fake_printer(
            printer_identity,
            material_snapshot=_material_snapshot(printer_identity.printer_id),
        )
        await adapter.connect()
        inventory, accounting, spool = _accounting(printer_identity.printer_id)
        policy = FilamentAccountingQueuePolicy(accounting, inventory)
        queue = QueueService(
            FleetService([adapter]),
            InMemoryQueueStore(),
            pre_dispatch_gate=policy,
            lifecycle_observer=policy,
        )
        entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "completion.gcode"),
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )
        accounting.plan(entry, (MaterialEstimate(0, Decimal("20")),))

        try:
            accepted = await queue.dispatch(entry.queue_id)
            assert accepted.receipt is not None and accepted.receipt.vendor_job_id is not None
            adapter.set_active_job(
                _job(accepted.receipt.vendor_job_id, JobState.COMPLETED),
                operational_state=OperationalState.COMPLETED,
            )
            await _wait_for_state(queue, entry.queue_id, QueueEntryState.COMPLETED)

            assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("80")
            reservation = accounting.reservations_for_queue(entry.queue_id)[0]
            assert reservation.state == FilamentReservationState.CONSUMED
            assert reservation.actual_mass_g == Decimal("20")
            assert len(inventory.adjustments(spool.spool_id)) == 1

            await queue.start()
            assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("80")
            assert len(inventory.adjustments(spool.spool_id)) == 1
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def test_failed_dispatch_attempt_requires_reconciliation_instead_of_release(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(
            printer_identity,
            material_snapshot=_material_snapshot(printer_identity.printer_id),
        )
        printing.fail_next_submit(
            PrinterAdapterError(
                PrinterErrorCode.CONNECTION_UNAVAILABLE,
                "simulated send failure",
                retryable=True,
            )
        )
        await adapter.connect()
        inventory, accounting, spool = _accounting(printer_identity.printer_id)
        policy = FilamentAccountingQueuePolicy(accounting, inventory)
        queue = QueueService(
            FleetService([adapter]),
            InMemoryQueueStore(),
            pre_dispatch_gate=policy,
            lifecycle_observer=policy,
        )
        entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "failed-attempt.gcode"),
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )
        accounting.plan(entry, (MaterialEstimate(0, Decimal("20")),))

        try:
            failed = await queue.dispatch(entry.queue_id)
            assert failed.state == QueueEntryState.FAILED
            assert failed.attempt_count == 1
            reservation = accounting.reservations_for_queue(entry.queue_id)[0]
            assert reservation.state == FilamentReservationState.RECONCILIATION_REQUIRED
            assert reservation.holds_capacity is True
            assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def test_indeterminate_dispatch_keeps_reservation_held(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(
            printer_identity,
            material_snapshot=_material_snapshot(printer_identity.printer_id),
        )
        printing.make_next_submit_indeterminate()
        await adapter.connect()
        inventory, accounting, spool = _accounting(printer_identity.printer_id)
        policy = FilamentAccountingQueuePolicy(accounting, inventory)
        queue = QueueService(
            FleetService([adapter]),
            InMemoryQueueStore(),
            pre_dispatch_gate=policy,
            lifecycle_observer=policy,
        )
        entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "indeterminate.gcode"),
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )
        accounting.plan(entry, (MaterialEstimate(0, Decimal("20")),))

        try:
            uncertain = await queue.dispatch(entry.queue_id)
            assert uncertain.state == QueueEntryState.INDETERMINATE
            reservation = accounting.reservations_for_queue(entry.queue_id)[0]
            assert reservation.state == FilamentReservationState.RESERVED
            assert reservation.holds_capacity is True
            assert accounting.reserved_mass(spool.spool_id) == Decimal("20")
            assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def test_restart_reconciles_durable_completed_queue_without_double_debit(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        database = tmp_path / "foxforge.sqlite3"
        inventory = InventoryService(SQLiteInventoryStore(database))
        spool = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal("100"))
        inventory.assign_spool(spool.spool_id, printer_identity.printer_id, _SLOT_ID)
        accounting = FilamentAccountingService(inventory, SQLiteFilamentAccountingStore(database))
        policy = FilamentAccountingQueuePolicy(accounting, inventory)

        adapter, _, _ = build_fake_printer(
            printer_identity,
            material_snapshot=_material_snapshot(printer_identity.printer_id),
        )
        await adapter.connect()
        fleet = FleetService([adapter])
        queue_store = SQLiteQueueStore(database)
        first = QueueService(fleet, queue_store, pre_dispatch_gate=policy)
        entry = first.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "restart-completed.gcode"),
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )
        accounting.plan(entry, (MaterialEstimate(0, Decimal("20")),))
        accepted = await first.dispatch(entry.queue_id)
        assert accepted.receipt is not None
        await first.aclose()

        queue_store.save(replace(accepted, state=QueueEntryState.COMPLETED, updated_at=utc_now()))
        assert accounting.reservations_for_queue(entry.queue_id)[0].state == FilamentReservationState.RESERVED

        restarted_inventory = InventoryService(SQLiteInventoryStore(database))
        restarted_accounting = FilamentAccountingService(
            restarted_inventory,
            SQLiteFilamentAccountingStore(database),
        )
        restarted_policy = FilamentAccountingQueuePolicy(restarted_accounting, restarted_inventory)
        restored = QueueService(
            fleet,
            SQLiteQueueStore(database),
            pre_dispatch_gate=restarted_policy,
            lifecycle_observer=restarted_policy,
        )

        try:
            await restored.start()
            assert restored.get(entry.queue_id).state == QueueEntryState.COMPLETED
            assert restarted_inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("80")
            assert len(restarted_inventory.adjustments(spool.spool_id)) == 1
            reservation = restarted_accounting.reservations_for_queue(entry.queue_id)[0]
            assert reservation.state == FilamentReservationState.CONSUMED

            await restored.start()
            assert restarted_inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("80")
            assert len(restarted_inventory.adjustments(spool.spool_id)) == 1
        finally:
            await restored.aclose()

    asyncio.run(scenario())
