# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from threading import RLock
from uuid import UUID

from foxforge.application.inventory import (
    ArchivedSpoolError,
    InventoryBalanceError,
    InventoryIdempotencyConflictError,
    InventoryService,
    SpoolNotFoundError,
)
from foxforge.application.queue import QueueEntry, QueueEntryState
from foxforge.domain.printers.capabilities import MaterialBinding

from .models import FilamentReservation, FilamentReservationState, MaterialEstimate
from .store import FilamentAccountingStore, FilamentAccountingStoreConflictError


class FilamentAccountingError(RuntimeError):
    pass


class FilamentPlanConflictError(FilamentAccountingError):
    pass


class FilamentAssignmentRequiredError(FilamentAccountingError):
    pass


class FilamentCapacityError(FilamentAccountingError):
    pass


class FilamentReconciliationRequiredError(FilamentAccountingError):
    pass


class FilamentReconciliationConflictError(FilamentAccountingError):
    pass


class FilamentSettlementError(FilamentAccountingError):
    pass


class FilamentSettlementConflictError(FilamentSettlementError):
    pass


class FilamentReservationNotFoundError(KeyError):
    pass


class FilamentAccountingService:
    """Vendor-independent reservation and settlement coordinator.

    Material estimates are explicit application input. This service never
    derives grams from print progress or vendor telemetry. It does not invoke
    printer adapters or participate in dispatch yet; the Candidate 6 R3 slice
    installs the pre-dispatch accounting gate in the current QueueService.
    """

    def __init__(
        self,
        inventory: InventoryService,
        store: FilamentAccountingStore,
        *,
        on_change: Callable[[UUID], None] | None = None,
    ) -> None:
        self._inventory = inventory
        self._store = store
        self._on_change = on_change
        self._lock = RLock()

    def preview_plan(
        self,
        printer_id: str,
        bindings: tuple[MaterialBinding, ...],
        estimates: tuple[MaterialEstimate, ...],
    ) -> tuple[tuple[MaterialEstimate, UUID, str], ...]:
        with self._lock:
            return self._resolve_plan(printer_id, bindings, estimates)

    def plan(
        self,
        entry: QueueEntry,
        estimates: tuple[MaterialEstimate, ...],
    ) -> tuple[FilamentReservation, ...]:
        with self._lock:
            bindings = _bindings_by_index(entry.request.material_bindings)
            estimate_map = _estimates_by_index(estimates)
            _require_exact_coverage(bindings, estimate_map)

            existing = self._store.list_for_queue(entry.queue_id)
            if existing:
                expected = {
                    material_index: (
                        estimate_map[material_index].estimated_mass_g,
                        entry.printer_id,
                        binding.slot_id,
                    )
                    for material_index, binding in bindings.items()
                }
                persisted = {
                    reservation.material_index: (
                        reservation.estimated_mass_g,
                        reservation.printer_id,
                        reservation.slot_id,
                    )
                    for reservation in existing
                }
                if expected != persisted:
                    raise FilamentPlanConflictError("filament plan is immutable once reservations are created")
                return existing

            resolved = self._resolve_plan(entry.printer_id, entry.request.material_bindings, estimates)
            now = datetime.now(UTC)
            reservations = tuple(
                FilamentReservation(
                    queue_id=entry.queue_id,
                    material_index=estimate.material_index,
                    spool_id=spool_id,
                    printer_id=entry.printer_id,
                    slot_id=slot_id,
                    estimated_mass_g=estimate.estimated_mass_g,
                    state=FilamentReservationState.RESERVED,
                    created_at=now,
                    updated_at=now,
                )
                for estimate, spool_id, slot_id in resolved
            )
            try:
                self._store.create_many(reservations)
            except FilamentAccountingStoreConflictError as error:
                raise FilamentPlanConflictError(str(error)) from error
            if reservations:
                self._changed(entry.queue_id)
            return reservations

    def reservations(self) -> tuple[FilamentReservation, ...]:
        return self._store.list()

    def reservations_for_queue(self, queue_id: UUID) -> tuple[FilamentReservation, ...]:
        return self._store.list_for_queue(queue_id)

    def reserved_mass(self, spool_id: UUID) -> Decimal:
        return sum(
            (
                reservation.estimated_mass_g
                for reservation in self._store.list_for_spool(spool_id)
                if reservation.holds_capacity
            ),
            start=Decimal("0"),
        )

    def available_mass(self, spool_id: UUID) -> Decimal:
        return self._inventory.balance(spool_id).remaining_filament_mass_g - self.reserved_mass(spool_id)

    def release_unstarted(self, entry: QueueEntry) -> tuple[FilamentReservation, ...]:
        with self._lock:
            if (
                entry.receipt is not None
                or entry.attempt_count != 0
                or entry.state
                not in {
                    QueueEntryState.PENDING,
                    QueueEntryState.BLOCKED,
                    QueueEntryState.FAILED,
                }
            ):
                raise FilamentReconciliationRequiredError(
                    "only confirmed pre-start queue entries may release reservations"
                )
            changed = tuple(
                self._release(reservation, "operator released reservation before confirmed print start")
                for reservation in self._store.list_for_queue(entry.queue_id)
                if reservation.state == FilamentReservationState.RESERVED
            )
            if changed:
                self._changed(entry.queue_id)
            return changed

    def sync_queue_entry(self, entry: QueueEntry) -> tuple[FilamentReservation, ...]:
        with self._lock:
            reservations = self._store.list_for_queue(entry.queue_id)
            if not reservations:
                return ()

            changed: list[FilamentReservation] = []
            if entry.state == QueueEntryState.COMPLETED:
                for reservation in reservations:
                    if reservation.state == FilamentReservationState.RESERVED:
                        changed.append(self._consume_estimate(reservation))
            elif entry.state == QueueEntryState.FAILED and entry.receipt is None and entry.attempt_count == 0:
                for reservation in reservations:
                    if reservation.state == FilamentReservationState.RESERVED:
                        changed.append(
                            self._release(
                                reservation,
                                "confirmed pre-start failure; no dispatch attempt crossed the start boundary",
                            )
                        )
            elif entry.state in {QueueEntryState.CANCELLED, QueueEntryState.FAILED} and (
                entry.receipt is not None or entry.attempt_count > 0
            ):
                for reservation in reservations:
                    if reservation.state == FilamentReservationState.RESERVED:
                        changed.append(
                            self._require_reconciliation(
                                reservation,
                                f"queue ended as {entry.state.value} after the dispatch start boundary",
                            )
                        )

            if changed:
                self._changed(entry.queue_id)
            return tuple(changed)

    def reconcile(
        self,
        queue_id: UUID,
        material_index: int,
        *,
        actual_mass_g: Decimal,
        note: str | None = None,
    ) -> FilamentReservation:
        actual = _nonnegative_mass(actual_mass_g, field_name="actual_mass_g")
        with self._lock:
            reservation = self._store.get(queue_id, material_index)
            if reservation is None:
                raise FilamentReservationNotFoundError(f"{queue_id}/{material_index}")

            if reservation.state == FilamentReservationState.CONSUMED:
                if reservation.actual_mass_g == actual:
                    return reservation
                raise FilamentReconciliationConflictError(
                    "reservation was already reconciled with a different consumed mass"
                )
            if reservation.state == FilamentReservationState.RELEASED:
                if actual == 0:
                    return reservation
                raise FilamentReconciliationConflictError(
                    "reservation was already reconciled/released with zero consumption"
                )
            if reservation.state != FilamentReservationState.RECONCILIATION_REQUIRED:
                raise FilamentReconciliationRequiredError("reservation is not awaiting reconciliation")

            if actual == 0:
                reconciled = self._release(reservation, note or "reconciled with zero material consumption")
            else:
                try:
                    adjustment = self._inventory.consume(
                        reservation.spool_id,
                        actual,
                        idempotency_key=self._reconciliation_key(reservation),
                        note=f"FoxForge queue {queue_id} reconciled material consumption",
                    )
                except InventoryBalanceError as error:
                    raise FilamentCapacityError(str(error)) from error
                except InventoryIdempotencyConflictError as error:
                    raise FilamentReconciliationConflictError(str(error)) from error
                except (ArchivedSpoolError, SpoolNotFoundError) as error:
                    raise FilamentSettlementError(str(error)) from error
                reconciled = replace(
                    reservation,
                    state=FilamentReservationState.CONSUMED,
                    actual_mass_g=-adjustment.delta_filament_mass_g,
                    updated_at=datetime.now(UTC),
                    note=note,
                )
                self._store.save(reconciled)
            self._changed(queue_id)
            return reconciled

    def reconcile_all(self, queue_entries: tuple[QueueEntry, ...]) -> None:
        by_id = {entry.queue_id: entry for entry in queue_entries}
        processed: set[UUID] = set()
        for reservation in self._store.list():
            if reservation.queue_id in processed:
                continue
            processed.add(reservation.queue_id)
            entry = by_id.get(reservation.queue_id)
            if entry is not None:
                self.sync_queue_entry(entry)

    def _resolve_plan(
        self,
        printer_id: str,
        bindings: tuple[MaterialBinding, ...],
        estimates: tuple[MaterialEstimate, ...],
    ) -> tuple[tuple[MaterialEstimate, UUID, str], ...]:
        by_index = _bindings_by_index(bindings)
        estimate_map = _estimates_by_index(estimates)
        _require_exact_coverage(by_index, estimate_map)
        if not estimates:
            return ()

        resolved: list[tuple[MaterialEstimate, UUID, str]] = []
        pending_by_spool: dict[UUID, Decimal] = {}
        for estimate in estimates:
            binding = by_index[estimate.material_index]
            assignment = self._inventory.assignment_for_slot(printer_id, binding.slot_id)
            if assignment is None:
                raise FilamentAssignmentRequiredError(
                    f"no FoxForge spool is assigned to {printer_id}/{binding.slot_id}"
                )
            try:
                spool = self._inventory.get_spool(assignment.spool_id)
            except SpoolNotFoundError as error:
                raise FilamentAssignmentRequiredError(str(error)) from error
            if spool.archived:
                raise FilamentAssignmentRequiredError("archived spool cannot be reserved for a print")

            already_held = self.reserved_mass(assignment.spool_id)
            pending = pending_by_spool.get(assignment.spool_id, Decimal("0"))
            available = self._inventory.balance(assignment.spool_id).remaining_filament_mass_g - already_held - pending
            if estimate.estimated_mass_g > available:
                raise FilamentCapacityError(
                    f"spool {assignment.spool_id} has {available} g available after active reservations; "
                    f"{estimate.estimated_mass_g} g requested"
                )
            pending_by_spool[assignment.spool_id] = pending + estimate.estimated_mass_g
            resolved.append((estimate, assignment.spool_id, binding.slot_id))
        return tuple(resolved)

    def _consume_estimate(self, reservation: FilamentReservation) -> FilamentReservation:
        try:
            adjustment = self._inventory.consume(
                reservation.spool_id,
                reservation.estimated_mass_g,
                idempotency_key=self._completion_key(reservation),
                note=f"FoxForge queue {reservation.queue_id} completed estimated consumption",
            )
        except InventoryBalanceError as error:
            return self._require_reconciliation(
                reservation,
                f"automatic completion accounting failed: {error}",
            )
        except InventoryIdempotencyConflictError as error:
            raise FilamentSettlementConflictError(str(error)) from error
        except (ArchivedSpoolError, SpoolNotFoundError) as error:
            raise FilamentSettlementError(str(error)) from error

        consumed = replace(
            reservation,
            state=FilamentReservationState.CONSUMED,
            actual_mass_g=-adjustment.delta_filament_mass_g,
            updated_at=datetime.now(UTC),
            note="settled automatically from completion estimate",
        )
        self._store.save(consumed)
        return consumed

    def _release(self, reservation: FilamentReservation, note: str) -> FilamentReservation:
        released = replace(
            reservation,
            state=FilamentReservationState.RELEASED,
            actual_mass_g=Decimal("0"),
            updated_at=datetime.now(UTC),
            note=note,
        )
        self._store.save(released)
        return released

    def _require_reconciliation(self, reservation: FilamentReservation, note: str) -> FilamentReservation:
        pending = replace(
            reservation,
            state=FilamentReservationState.RECONCILIATION_REQUIRED,
            updated_at=datetime.now(UTC),
            note=note,
        )
        self._store.save(pending)
        return pending

    @staticmethod
    def _completion_key(reservation: FilamentReservation) -> str:
        return f"foxforge:queue:{reservation.queue_id}:material:{reservation.material_index}:completion"

    @staticmethod
    def _reconciliation_key(reservation: FilamentReservation) -> str:
        return f"foxforge:queue:{reservation.queue_id}:material:{reservation.material_index}:reconciliation"

    def _changed(self, queue_id: UUID) -> None:
        if self._on_change is not None:
            self._on_change(queue_id)


def _bindings_by_index(bindings: tuple[MaterialBinding, ...]) -> dict[int, MaterialBinding]:
    by_index = {binding.material_index: binding for binding in bindings}
    if len(by_index) != len(bindings):
        raise FilamentPlanConflictError("queue material bindings contain duplicate material indices")
    return by_index


def _estimates_by_index(estimates: tuple[MaterialEstimate, ...]) -> dict[int, MaterialEstimate]:
    by_index = {estimate.material_index: estimate for estimate in estimates}
    if len(by_index) != len(estimates):
        raise FilamentPlanConflictError("material estimates contain duplicate material indices")
    return by_index


def _require_exact_coverage(
    bindings: dict[int, MaterialBinding],
    estimates: dict[int, MaterialEstimate],
) -> None:
    if set(bindings) != set(estimates):
        raise FilamentPlanConflictError("material estimates must cover every queue material binding exactly once")


def _nonnegative_mass(value: Decimal, *, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be Decimal")
    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value
