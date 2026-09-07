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
    FilamentCapacityError,
    FilamentPlanConflictError,
    FilamentReconciliationConflictError,
    FilamentReconciliationRequiredError,
    FilamentReservationState,
    InMemoryFilamentAccountingStore,
    MaterialEstimate,
)
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import QueueDispatchError, QueueEntry, QueueEntryState
from foxforge.domain.printers import PrinterErrorCode
from foxforge.domain.printers.capabilities import MaterialBinding, PrintDispatchReceipt, PrintExecutionRequest
from tests.helpers import make_artifact


def _entry(tmp_path, *, bindings: tuple[MaterialBinding, ...] | None = None) -> QueueEntry:
    now = datetime.now(UTC)
    artifact = make_artifact(tmp_path / f"{uuid4()}.gcode")
    return QueueEntry(
        queue_id=uuid4(),
        printer_id="printer-1",
        request=PrintExecutionRequest(
            dispatch_id=uuid4(),
            artifact=artifact,
            material_bindings=bindings or (MaterialBinding(material_index=0, slot_id="opaque-slot-1"),),
        ),
        state=QueueEntryState.PENDING,
        created_at=now,
        updated_at=now,
    )


def _receipt(entry: QueueEntry, vendor_job_id: str = "vendor-job-1") -> PrintDispatchReceipt:
    return PrintDispatchReceipt(
        dispatch_id=entry.request.dispatch_id,
        accepted_at=datetime.now(UTC),
        vendor_job_id=vendor_job_id,
        artifact_sha256=entry.request.artifact.sha256,
    )


def _services(*, mass: str = "100"):
    inventory = InventoryService(InMemoryInventoryStore())
    spool = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal(mass))
    inventory.assign_spool(spool.spool_id, "printer-1", "opaque-slot-1")
    accounting = FilamentAccountingService(inventory, InMemoryFilamentAccountingStore())
    return inventory, accounting, spool


def test_plan_reserves_capacity_without_debit_and_prevents_overcommit(tmp_path) -> None:
    inventory, accounting, spool = _services()
    first = _entry(tmp_path)
    accounting.plan(first, (MaterialEstimate(0, Decimal("60")),))

    assert accounting.reserved_mass(spool.spool_id) == Decimal("60")
    assert accounting.available_mass(spool.spool_id) == Decimal("40")
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")

    second = _entry(tmp_path)
    with pytest.raises(FilamentCapacityError):
        accounting.plan(second, (MaterialEstimate(0, Decimal("41")),))
    assert accounting.reservations_for_queue(second.queue_id) == ()


def test_plan_aggregates_multiple_material_indices_using_same_physical_spool(tmp_path) -> None:
    _, accounting, _ = _services()
    bindings = (
        MaterialBinding(material_index=0, slot_id="opaque-slot-1"),
        MaterialBinding(material_index=1, slot_id="opaque-slot-1"),
    )

    with pytest.raises(FilamentCapacityError):
        accounting.preview_plan(
            "printer-1",
            bindings,
            (MaterialEstimate(0, Decimal("60")), MaterialEstimate(1, Decimal("41"))),
        )


def test_existing_plan_is_idempotent_but_immutable(tmp_path) -> None:
    _, accounting, _ = _services()
    entry = _entry(tmp_path)
    first = accounting.plan(entry, (MaterialEstimate(0, Decimal("25")),))
    assert accounting.plan(entry, (MaterialEstimate(0, Decimal("25")),)) == first

    with pytest.raises(FilamentPlanConflictError):
        accounting.plan(entry, (MaterialEstimate(0, Decimal("26")),))


def test_completed_queue_consumes_estimate_exactly_once(tmp_path) -> None:
    inventory, accounting, spool = _services()
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("25")),))
    completed = replace(
        entry,
        state=QueueEntryState.COMPLETED,
        receipt=_receipt(entry),
        updated_at=datetime.now(UTC),
    )

    first = accounting.sync_queue_entry(completed)
    second = accounting.sync_queue_entry(completed)

    assert first[0].state == FilamentReservationState.CONSUMED
    assert first[0].actual_mass_g == Decimal("25")
    assert second == ()
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("75")
    assert len(inventory.adjustments(spool.spool_id)) == 1


def test_prestart_failure_releases_without_consuming(tmp_path) -> None:
    inventory, accounting, spool = _services()
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("30")),))
    failed = replace(entry, state=QueueEntryState.FAILED, updated_at=datetime.now(UTC))

    changed = accounting.sync_queue_entry(failed)

    assert changed[0].state == FilamentReservationState.RELEASED
    assert accounting.reserved_mass(spool.spool_id) == Decimal("0")
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")
    assert inventory.adjustments(spool.spool_id) == ()


def test_receipt_free_failure_after_dispatch_attempt_requires_reconciliation(tmp_path) -> None:
    inventory, accounting, spool = _services()
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("30")),))
    now = datetime.now(UTC)
    failed = replace(
        entry,
        state=QueueEntryState.FAILED,
        error=QueueDispatchError(
            code=PrinterErrorCode.INTERNAL_ADAPTER_ERROR,
            message="adapter returned an invalid receipt after submit",
            retryable=False,
        ),
        attempt_count=1,
        last_attempt_at=now,
        updated_at=now,
    )

    changed = accounting.sync_queue_entry(failed)

    assert changed[0].state == FilamentReservationState.RECONCILIATION_REQUIRED
    assert changed[0].holds_capacity is True
    assert accounting.reserved_mass(spool.spool_id) == Decimal("30")
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")
    assert inventory.adjustments(spool.spool_id) == ()
    with pytest.raises(FilamentReconciliationRequiredError):
        accounting.release_unstarted(failed)


@pytest.mark.parametrize("state", [QueueEntryState.FAILED, QueueEntryState.CANCELLED])
def test_started_failed_or_cancelled_job_requires_explicit_reconciliation(tmp_path, state: QueueEntryState) -> None:
    inventory, accounting, spool = _services()
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("30")),))
    terminal = replace(
        entry,
        state=state,
        receipt=_receipt(entry),
        updated_at=datetime.now(UTC),
    )

    pending = accounting.sync_queue_entry(terminal)[0]

    assert pending.state == FilamentReservationState.RECONCILIATION_REQUIRED
    assert pending.holds_capacity is True
    assert accounting.reserved_mass(spool.spool_id) == Decimal("30")
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")


def test_indeterminate_dispatch_keeps_reservation_held_and_unchanged(tmp_path) -> None:
    inventory, accounting, spool = _services()
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("20")),))
    now = datetime.now(UTC)
    uncertain = replace(
        entry,
        state=QueueEntryState.INDETERMINATE,
        error=QueueDispatchError(
            code=PrinterErrorCode.INDETERMINATE,
            message="printer acceptance is unknown",
            retryable=False,
        ),
        attempt_count=1,
        last_attempt_at=now,
        updated_at=now,
    )

    assert accounting.sync_queue_entry(uncertain) == ()
    reservation = accounting.reservations_for_queue(entry.queue_id)[0]
    assert reservation.state == FilamentReservationState.RESERVED
    assert reservation.holds_capacity is True
    assert accounting.reserved_mass(spool.spool_id) == Decimal("20")
    assert inventory.adjustments(spool.spool_id) == ()


def test_explicit_positive_reconciliation_is_service_level_idempotent(tmp_path) -> None:
    inventory, accounting, spool = _services()
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("30")),))
    cancelled = replace(
        entry,
        state=QueueEntryState.CANCELLED,
        receipt=_receipt(entry),
        updated_at=datetime.now(UTC),
    )
    accounting.sync_queue_entry(cancelled)

    first = accounting.reconcile(entry.queue_id, 0, actual_mass_g=Decimal("12.5"), note="weighed")
    replay = accounting.reconcile(entry.queue_id, 0, actual_mass_g=Decimal("12.5"), note="replayed")

    assert replay == first
    assert first.state == FilamentReservationState.CONSUMED
    assert first.actual_mass_g == Decimal("12.5")
    assert accounting.reserved_mass(spool.spool_id) == Decimal("0")
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("87.5")
    assert len(inventory.adjustments(spool.spool_id)) == 1

    with pytest.raises(FilamentReconciliationConflictError):
        accounting.reconcile(entry.queue_id, 0, actual_mass_g=Decimal("13"))


def test_zero_reconciliation_releases_idempotently(tmp_path) -> None:
    inventory, accounting, spool = _services()
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("15")),))
    failed = replace(
        entry,
        state=QueueEntryState.FAILED,
        receipt=_receipt(entry),
        updated_at=datetime.now(UTC),
    )
    accounting.sync_queue_entry(failed)

    first = accounting.reconcile(entry.queue_id, 0, actual_mass_g=Decimal("0"))
    replay = accounting.reconcile(entry.queue_id, 0, actual_mass_g=Decimal("0"))

    assert replay == first
    assert first.state == FilamentReservationState.RELEASED
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("100")
    assert inventory.adjustments(spool.spool_id) == ()

    with pytest.raises(FilamentReconciliationConflictError):
        accounting.reconcile(entry.queue_id, 0, actual_mass_g=Decimal("1"))


def test_release_unstarted_is_fail_closed_after_dispatch_boundary(tmp_path) -> None:
    _, accounting, _ = _services()
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("10")),))
    now = datetime.now(UTC)
    dispatching = replace(
        entry,
        state=QueueEntryState.DISPATCHING,
        attempt_count=1,
        last_attempt_at=now,
        updated_at=now,
    )

    with pytest.raises(FilamentReconciliationRequiredError):
        accounting.release_unstarted(dispatching)


def test_completion_balance_failure_requires_reconciliation_without_guessing_usage(tmp_path) -> None:
    inventory, accounting, spool = _services()
    entry = _entry(tmp_path)
    accounting.plan(entry, (MaterialEstimate(0, Decimal("80")),))
    inventory.consume(spool.spool_id, Decimal("30"), idempotency_key="manual:parallel-use")
    completed = replace(
        entry,
        state=QueueEntryState.COMPLETED,
        receipt=_receipt(entry),
        updated_at=datetime.now(UTC),
    )

    changed = accounting.sync_queue_entry(completed)

    assert changed[0].state == FilamentReservationState.RECONCILIATION_REQUIRED
    assert changed[0].actual_mass_g is None
    assert changed[0].holds_capacity is True
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("70")
    assert len(inventory.adjustments(spool.spool_id)) == 1
