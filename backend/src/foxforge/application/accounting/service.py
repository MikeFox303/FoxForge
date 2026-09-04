# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Callable
from uuid import UUID

from foxforge.application.inventory import InventoryBalanceError, InventoryService
from foxforge.application.queue import QueueEntry, QueueEntryState

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


class FilamentReservationNotFoundError(KeyError):
    pass


class FilamentAccountingService:
    """Durable queue-to-spool reservation and consumption coordinator.

    Estimates are explicit application input. FoxForge never derives grams from
    printer progress or vendor payloads here. Queue completion may settle the
    estimate automatically; ambiguous/partial outcomes require reconciliation.
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

    def preview_plan(
        self,
        entry: QueueEntry,
        estimates: tuple[MaterialEstimate, ...],
    ) -> tuple[tuple[MaterialEstimate, UUID, str], ...]:
        if not estimates:
            return ()
        by_index = {binding.material_index: binding for binding in entry.request.material_bindings}
        if len(by_index) != len(entry.request.material_bindings):
            raise FilamentPlanConflictError("queue material bindings contain duplicate material indices")
        estimate_indices = [estimate.material_index for estimate in estimates]
        if len(estimate_indices) != len(set(estimate_indices)):
            raise FilamentPlanConflictError("material estimates contain duplicate material indices")

        resolved: list[tuple[MaterialEstimate, UUID, str]] = []
        pending_by_spool: dict[UUID, Decimal] = {}
        for estimate in estimates:
            binding = by_index.get(estimate.material_index)
            if binding is None:
                raise FilamentPlanConflictError(
                    f"material estimate {estimate.material_index} has no matching queue material binding"
                )
            assignment = self._inventory.assignment_for_slot(entry.printer_id, binding.slot_id)
            if assignment is None:
                raise FilamentAssignmentRequiredError(
                    f"no FoxForge spool is assigned to {entry.printer_id}/{binding.slot_id}"
                )
            spool = self._inventory.get_spool(assignment.spool_id)
            if spool.archived:
                raise FilamentAssignmentRequiredError("archived spool cannot be reserved for a print")

            held = self.reserved_mass(assignment.spool_id) + pending_by_spool.get(
                assignment.spool_id, Decimal("0")
            )
            available = self._inventory.balance(assignment.spool_id).remaining_filament_mass_g - held
            if estimate.estimated_mass_g > available:
                raise FilamentCapacityError(
                    f"spool {assignment.spool_id} has {available} g available after active reservations; "
                    f"{estimate.estimated_mass_g} g requested"
                )
            pending_by_spool[assignment.spool_id] = (
                pending_by_spool.get(assignment.spool_id, Decimal("0")) + estimate.estimated_mass_g
            )
            resolved.append((estimate, assignment.spool_id, binding.slot_id))
        return tuple(resolved)

    def plan(
        self,
        entry: QueueEntry,
        estimates: tuple[MaterialEstimate, ...],
    ) -> tuple[FilamentReservation, ...]:
        resolved = self.preview_plan(entry, estimates)
        created: list[FilamentReservation] = []
        now = datetime.now(UTC)
        for estimate, spool_id, slot_id in resolved:
            existing = self._store.get(entry.queue_id, estimate.material_index)
            if existing is not None:
                if (
                    existing.spool_id == spool_id
                    and existing.printer_id == entry.printer_id
                    and existing.slot_id == slot_id
                    and existing.estimated_mass_g == estimate.estimated_mass_g
                ):
                    created.append(existing)
                    continue
                raise FilamentPlanConflictError(
                    f"reservation already exists with different data: {entry.queue_id}/{estimate.material_index}"
                )
            reservation = FilamentReservation(
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
            try:
                self._store.create(reservation)
            except FilamentAccountingStoreConflictError as error:
                raise FilamentPlanConflictError(str(error)) from error
            created.append(reservation)
        if created:
            self._changed(entry.queue_id)
        return tuple(created)

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

    def sync_queue_entry(self, entry: QueueEntry) -> tuple[FilamentReservation, ...]:
        reservations = self._store.list_for_queue(entry.queue_id)
        if not reservations:
            return ()

        changed: list[FilamentReservation] = []
        if entry.state == QueueEntryState.COMPLETED:
            for reservation in reservations:
                if reservation.state != FilamentReservationState.RESERVED:
                    continue
                changed.append(self._consume_estimate(reservation))
        elif entry.state == QueueEntryState.FAILED and entry.receipt is None:
            for reservation in reservations:
                if reservation.state == FilamentReservationState.RESERVED:
                    changed.append(self._release(reservation, "pre-start failure; no dispatch receipt"))
        elif entry.state in {QueueEntryState.CANCELLED, QueueEntryState.FAILED} and entry.receipt is not None:
            for reservation in reservations:
                if reservation.state == FilamentReservationState.RESERVED:
                    changed.append(
                        self._require_reconciliation(
                            reservation,
                            f"queue ended as {entry.state.value} after confirmed start",
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
        reservation = self._store.get(queue_id, material_index)
        if reservation is None:
            raise FilamentReservationNotFoundError(f"{queue_id}/{material_index}")
        if reservation.state != FilamentReservationState.RECONCILIATION_REQUIRED:
            raise FilamentReconciliationRequiredError("reservation is not awaiting reconciliation")
        if not isinstance(actual_mass_g, Decimal) or not actual_mass_g.is_finite() or actual_mass_g < 0:
            raise ValueError("actual_mass_g must be a non-negative finite Decimal")

        if actual_mass_g == 0:
            reconciled = self._release(reservation, note or "reconciled with zero material consumption")
        else:
            try:
                adjustment = self._inventory.consume(
                    reservation.spool_id,
                    actual_mass_g,
                    idempotency_key=self._reconciliation_key(reservation),
                    note=note or f"FoxForge queue {queue_id} reconciled material consumption",
                )
            except InventoryBalanceError as error:
                raise FilamentCapacityError(str(error)) from error
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
        for reservation in self._store.list():
            entry = by_id.get(reservation.queue_id)
            if entry is not None:
                self.sync_queue_entry(entry)

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
