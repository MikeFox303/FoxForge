# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from foxforge.application.accounting import (
    FilamentAccountingService,
    FilamentCapacityError,
    FilamentReservationState,
    InMemoryFilamentAccountingStore,
    MaterialEstimate,
)
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import QueueEntry, QueueEntryState
from foxforge.domain.printers.capabilities import (
    LocalPrintArtifact,
    MaterialBinding,
    PrintArtifactFormat,
    PrintDispatchReceipt,
    PrintExecutionRequest,
)


def _fixture() -> tuple[InventoryService, FilamentAccountingService, QueueEntry, object]:
    inventory = InventoryService(InMemoryInventoryStore())
    spool = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("100"))
    inventory.assign_spool(spool.spool_id, "printer-1", "ams:0")
    accounting = FilamentAccountingService(inventory, InMemoryFilamentAccountingStore())
    now = datetime.now(UTC)
    artifact = LocalPrintArtifact(
        artifact_id="a" * 64,
        path=Path("/data/artifacts/job.gcode"),
        filename="job.gcode",
        format=PrintArtifactFormat.GCODE,
        size_bytes=10,
        sha256="a" * 64,
    )
    request = PrintExecutionRequest(
        dispatch_id=uuid4(),
        artifact=artifact,
        material_bindings=(MaterialBinding(material_index=0, slot_id="ams:0"),),
    )
    entry = QueueEntry(
        queue_id=uuid4(),
        printer_id="printer-1",
        request=request,
        state=QueueEntryState.PENDING,
        created_at=now,
        updated_at=now,
    )
    return inventory, accounting, entry, spool


def test_reservation_reduces_available_mass_and_prevents_overcommit() -> None:
    inventory, accounting, entry, spool = _fixture()
    accounting.plan(entry, (MaterialEstimate(0, Decimal("60")),))

    assert accounting.reserved_mass(spool.spool_id) == Decimal("60")
    assert accounting.available_mass(spool.spool_id) == Decimal("40")
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")

    second = replace(entry, queue_id=uuid4())
    with pytest.raises(FilamentCapacityError):
        accounting.plan(second, (MaterialEstimate(0, Decimal("41")),))


def test_completed_queue_consumes_estimate_once() -> None:
    inventory, accounting, entry, spool = _fixture()
    accounting.plan(entry, (MaterialEstimate(0, Decimal("25")),))
    receipt = PrintDispatchReceipt(
        dispatch_id=entry.request.dispatch_id,
        accepted_at=datetime.now(UTC),
        vendor_job_id="job-1",
        artifact_sha256=entry.request.artifact.sha256,
    )
    completed = replace(entry, state=QueueEntryState.COMPLETED, receipt=receipt, updated_at=datetime.now(UTC))

    first = accounting.sync_queue_entry(completed)
    second = accounting.sync_queue_entry(completed)

    assert first[0].state == FilamentReservationState.CONSUMED
    assert second == ()
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("75")
    assert len(inventory.adjustments(spool.spool_id)) == 1


def test_prestart_failure_releases_without_consumption() -> None:
    inventory, accounting, entry, spool = _fixture()
    accounting.plan(entry, (MaterialEstimate(0, Decimal("30")),))
    failed = replace(entry, state=QueueEntryState.FAILED, updated_at=datetime.now(UTC))

    changed = accounting.sync_queue_entry(failed)

    assert changed[0].state == FilamentReservationState.RELEASED
    assert accounting.reserved_mass(spool.spool_id) == Decimal("0")
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")


def test_cancelled_started_job_requires_explicit_actual_mass_reconciliation() -> None:
    inventory, accounting, entry, spool = _fixture()
    accounting.plan(entry, (MaterialEstimate(0, Decimal("30")),))
    receipt = PrintDispatchReceipt(
        dispatch_id=entry.request.dispatch_id,
        accepted_at=datetime.now(UTC),
        vendor_job_id="job-2",
        artifact_sha256=entry.request.artifact.sha256,
    )
    cancelled = replace(entry, state=QueueEntryState.CANCELLED, receipt=receipt, updated_at=datetime.now(UTC))

    pending = accounting.sync_queue_entry(cancelled)[0]
    assert pending.state == FilamentReservationState.RECONCILIATION_REQUIRED
    assert accounting.reserved_mass(spool.spool_id) == Decimal("30")

    settled = accounting.reconcile(entry.queue_id, 0, actual_mass_g=Decimal("12.5"))
    assert settled.state == FilamentReservationState.CONSUMED
    assert settled.actual_mass_g == Decimal("12.5")
    assert accounting.reserved_mass(spool.spool_id) == Decimal("0")
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("87.5")
