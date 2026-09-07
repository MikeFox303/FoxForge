# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from foxforge.application.accounting import (
    FilamentAccountingService,
    FilamentAccountingStoreConflictError,
    FilamentReservation,
    FilamentReservationState,
    MaterialEstimate,
)
from foxforge.application.inventory import InventoryService
from foxforge.application.queue import QueueEntry, QueueEntryState
from foxforge.domain.printers.capabilities import MaterialBinding, PrintDispatchReceipt, PrintExecutionRequest
from foxforge.infrastructure.accounting import SQLiteFilamentAccountingStore
from foxforge.infrastructure.inventory import SQLiteInventoryStore
from tests.helpers import make_artifact


def _reservation(*, queue_id=None, material_index: int = 0) -> FilamentReservation:
    now = datetime.now(UTC)
    return FilamentReservation(
        queue_id=queue_id or uuid4(),
        material_index=material_index,
        spool_id=uuid4(),
        printer_id="printer-1",
        slot_id=f"opaque-slot-{material_index}",
        estimated_mass_g=Decimal("10"),
        state=FilamentReservationState.RESERVED,
        created_at=now,
        updated_at=now,
    )


def _entry(tmp_path) -> QueueEntry:
    now = datetime.now(UTC)
    artifact = make_artifact(tmp_path / "settlement.gcode")
    return QueueEntry(
        queue_id=uuid4(),
        printer_id="printer-1",
        request=PrintExecutionRequest(
            dispatch_id=uuid4(),
            artifact=artifact,
            material_bindings=(MaterialBinding(material_index=0, slot_id="opaque-slot-1"),),
        ),
        state=QueueEntryState.PENDING,
        created_at=now,
        updated_at=now,
    )


def _receipt(entry: QueueEntry) -> PrintDispatchReceipt:
    return PrintDispatchReceipt(
        dispatch_id=entry.request.dispatch_id,
        accepted_at=datetime.now(UTC),
        vendor_job_id="job-1",
        artifact_sha256=entry.request.artifact.sha256,
    )


def test_sqlite_create_many_rolls_back_entire_material_plan_on_conflict(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    store = SQLiteFilamentAccountingStore(database)
    queue_id = uuid4()
    existing = _reservation(queue_id=queue_id, material_index=1)
    store.create(existing)

    first_material = _reservation(queue_id=queue_id, material_index=0)
    conflicting_second = replace(existing, spool_id=uuid4(), updated_at=datetime.now(UTC))

    with pytest.raises(FilamentAccountingStoreConflictError):
        store.create_many((first_material, conflicting_second))

    reopened = SQLiteFilamentAccountingStore(database)
    assert reopened.list_for_queue(queue_id) == (existing,)
    assert reopened.get(queue_id, 0) is None


def test_completion_ledger_commit_before_reservation_save_recovers_exactly_once_after_restart(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    inventory = InventoryService(SQLiteInventoryStore(database))
    spool = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal("100"))
    inventory.assign_spool(spool.spool_id, "printer-1", "opaque-slot-1")
    accounting_store = SQLiteFilamentAccountingStore(database)
    accounting = FilamentAccountingService(inventory, accounting_store)
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("25")),))

    key = f"foxforge:queue:{entry.queue_id}:material:0:completion"
    note = f"FoxForge queue {entry.queue_id} completed estimated consumption"
    original_adjustment = inventory.consume(
        spool.spool_id,
        Decimal("25"),
        idempotency_key=key,
        note=note,
    )
    assert accounting_store.get(entry.queue_id, 0).state == FilamentReservationState.RESERVED  # type: ignore[union-attr]

    completed = replace(
        entry,
        state=QueueEntryState.COMPLETED,
        receipt=_receipt(entry),
        updated_at=datetime.now(UTC),
    )
    restarted_inventory = InventoryService(SQLiteInventoryStore(database))
    restarted_accounting = FilamentAccountingService(
        restarted_inventory,
        SQLiteFilamentAccountingStore(database),
    )
    changed = restarted_accounting.sync_queue_entry(completed)

    assert changed[0].state == FilamentReservationState.CONSUMED
    assert changed[0].actual_mass_g == Decimal("25")
    assert restarted_inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("75")
    assert restarted_inventory.adjustments(spool.spool_id) == (original_adjustment,)

    replayed = FilamentAccountingService(
        InventoryService(SQLiteInventoryStore(database)),
        SQLiteFilamentAccountingStore(database),
    )
    assert replayed.sync_queue_entry(completed) == ()
    final_inventory = InventoryService(SQLiteInventoryStore(database))
    assert final_inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("75")
    assert final_inventory.adjustments(spool.spool_id) == (original_adjustment,)


def test_reconciliation_ledger_commit_before_reservation_save_recovers_without_double_debit(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    inventory = InventoryService(SQLiteInventoryStore(database))
    spool = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("100"))
    inventory.assign_spool(spool.spool_id, "printer-1", "opaque-slot-1")
    accounting = FilamentAccountingService(inventory, SQLiteFilamentAccountingStore(database))
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("30")),))
    cancelled = replace(
        entry,
        state=QueueEntryState.CANCELLED,
        receipt=_receipt(entry),
        updated_at=datetime.now(UTC),
    )
    accounting.sync_queue_entry(cancelled)

    key = f"foxforge:queue:{entry.queue_id}:material:0:reconciliation"
    note = f"FoxForge queue {entry.queue_id} reconciled material consumption"
    original_adjustment = inventory.consume(
        spool.spool_id,
        Decimal("12.5"),
        idempotency_key=key,
        note=note,
    )

    restarted_inventory = InventoryService(SQLiteInventoryStore(database))
    restarted_accounting = FilamentAccountingService(
        restarted_inventory,
        SQLiteFilamentAccountingStore(database),
    )
    settled = restarted_accounting.reconcile(
        entry.queue_id,
        0,
        actual_mass_g=Decimal("12.5"),
        note="operator weighed spool",
    )

    assert settled.state == FilamentReservationState.CONSUMED
    assert settled.actual_mass_g == Decimal("12.5")
    assert restarted_inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("87.5")
    assert restarted_inventory.adjustments(spool.spool_id) == (original_adjustment,)

    replay = restarted_accounting.reconcile(entry.queue_id, 0, actual_mass_g=Decimal("12.5"))
    assert replay == settled
    assert restarted_inventory.adjustments(spool.spool_id) == (original_adjustment,)
