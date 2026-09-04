# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from foxforge.application.accounting import FilamentAccountingService, FilamentReservationState, MaterialEstimate
from foxforge.application.inventory import InventoryService
from foxforge.application.queue import QueueEntry, QueueEntryState
from foxforge.domain.printers.capabilities import (
    LocalPrintArtifact,
    MaterialBinding,
    PrintArtifactFormat,
    PrintDispatchReceipt,
    PrintExecutionRequest,
)
from foxforge.infrastructure.accounting import SQLiteFilamentAccountingStore
from foxforge.infrastructure.inventory import SQLiteInventoryStore


def _entry() -> QueueEntry:
    now = datetime.now(UTC)
    request = PrintExecutionRequest(
        dispatch_id=uuid4(),
        artifact=LocalPrintArtifact(
            artifact_id="a" * 64,
            path=Path("/data/artifacts/job.gcode"),
            filename="job.gcode",
            format=PrintArtifactFormat.GCODE,
            size_bytes=10,
            sha256="a" * 64,
        ),
        material_bindings=(MaterialBinding(material_index=0, slot_id="slot-0"),),
    )
    return QueueEntry(
        queue_id=uuid4(),
        printer_id="printer-1",
        request=request,
        state=QueueEntryState.PENDING,
        created_at=now,
        updated_at=now,
    )


def test_sqlite_reservation_survives_restart(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    inventory = InventoryService(SQLiteInventoryStore(database))
    spool = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("100"))
    inventory.assign_spool(spool.spool_id, "printer-1", "slot-0")
    entry = _entry()

    first = FilamentAccountingService(inventory, SQLiteFilamentAccountingStore(database))
    first.plan(entry, (MaterialEstimate(0, Decimal("25")),))

    second_inventory = InventoryService(SQLiteInventoryStore(database))
    second = FilamentAccountingService(second_inventory, SQLiteFilamentAccountingStore(database))
    restored = second.reservations_for_queue(entry.queue_id)

    assert len(restored) == 1
    assert restored[0].state == FilamentReservationState.RESERVED
    assert restored[0].estimated_mass_g == Decimal("25")
    assert restored[0].spool_id == spool.spool_id
    assert second.available_mass(spool.spool_id) == Decimal("75")


def test_restart_after_inventory_commit_does_not_double_consume(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    inventory = InventoryService(SQLiteInventoryStore(database))
    spool = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal("100"))
    inventory.assign_spool(spool.spool_id, "printer-1", "slot-0")
    entry = _entry()
    accounting = FilamentAccountingService(inventory, SQLiteFilamentAccountingStore(database))
    accounting.plan(entry, (MaterialEstimate(0, Decimal("25")),))

    completion_key = f"foxforge:queue:{entry.queue_id}:material:0:completion"
    completion_note = f"FoxForge queue {entry.queue_id} completed estimated consumption"
    inventory.consume(
        spool.spool_id,
        Decimal("25"),
        idempotency_key=completion_key,
        note=completion_note,
    )
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("75")
    assert accounting.reservations_for_queue(entry.queue_id)[0].state == FilamentReservationState.RESERVED

    receipt = PrintDispatchReceipt(
        dispatch_id=entry.request.dispatch_id,
        accepted_at=datetime.now(UTC),
        vendor_job_id="job-1",
        artifact_sha256=entry.request.artifact.sha256,
    )
    completed = replace(
        entry,
        state=QueueEntryState.COMPLETED,
        receipt=receipt,
        updated_at=datetime.now(UTC),
    )

    restarted_inventory = InventoryService(SQLiteInventoryStore(database))
    restarted = FilamentAccountingService(
        restarted_inventory,
        SQLiteFilamentAccountingStore(database),
    )
    restarted.reconcile_all((completed,))

    settled = restarted.reservations_for_queue(entry.queue_id)[0]
    assert settled.state == FilamentReservationState.CONSUMED
    assert settled.actual_mass_g == Decimal("25")
    assert restarted_inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("75")
    assert len(restarted_inventory.adjustments(spool.spool_id)) == 1
