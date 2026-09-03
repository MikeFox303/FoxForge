# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from foxforge.domain.inventory import Spool, SpoolAdjustment, SpoolAssignment


class InventoryStoreConflictError(RuntimeError):
    pass


class InventoryStoreMissingError(RuntimeError):
    pass


class InventoryStore(Protocol):
    def create_spool(self, spool: Spool) -> None: ...

    def save_spool(self, spool: Spool) -> None: ...

    def get_spool(self, spool_id: UUID) -> Spool | None: ...

    def list_spools(self) -> tuple[Spool, ...]: ...

    def append_adjustment(self, adjustment: SpoolAdjustment) -> None: ...

    def get_adjustment_by_key(self, idempotency_key: str) -> SpoolAdjustment | None: ...

    def list_adjustments(self, spool_id: UUID) -> tuple[SpoolAdjustment, ...]: ...

    def save_assignment(self, assignment: SpoolAssignment) -> None: ...

    def delete_assignment(self, spool_id: UUID) -> None: ...

    def assignment_for_spool(self, spool_id: UUID) -> SpoolAssignment | None: ...

    def assignment_for_slot(self, printer_id: str, slot_id: str) -> SpoolAssignment | None: ...

    def list_assignments(self) -> tuple[SpoolAssignment, ...]: ...


class InMemoryInventoryStore:
    """Deterministic inventory store for domain/application tests."""

    def __init__(self) -> None:
        self._spools: dict[UUID, Spool] = {}
        self._adjustments: dict[UUID, SpoolAdjustment] = {}
        self._adjustment_keys: dict[str, UUID] = {}
        self._assignments_by_spool: dict[UUID, SpoolAssignment] = {}
        self._assignments_by_slot: dict[tuple[str, str], UUID] = {}

    def create_spool(self, spool: Spool) -> None:
        if spool.spool_id in self._spools:
            raise InventoryStoreConflictError(f"spool already exists: {spool.spool_id}")
        self._spools[spool.spool_id] = spool

    def save_spool(self, spool: Spool) -> None:
        if spool.spool_id not in self._spools:
            raise InventoryStoreMissingError(f"spool does not exist: {spool.spool_id}")
        self._spools[spool.spool_id] = spool

    def get_spool(self, spool_id: UUID) -> Spool | None:
        return self._spools.get(spool_id)

    def list_spools(self) -> tuple[Spool, ...]:
        return tuple(sorted(self._spools.values(), key=lambda spool: (spool.created_at, str(spool.spool_id))))

    def append_adjustment(self, adjustment: SpoolAdjustment) -> None:
        if adjustment.adjustment_id in self._adjustments:
            raise InventoryStoreConflictError(f"adjustment already exists: {adjustment.adjustment_id}")
        if adjustment.idempotency_key in self._adjustment_keys:
            raise InventoryStoreConflictError(f"adjustment key already exists: {adjustment.idempotency_key}")
        if adjustment.spool_id not in self._spools:
            raise InventoryStoreMissingError(f"spool does not exist: {adjustment.spool_id}")
        self._adjustments[adjustment.adjustment_id] = adjustment
        self._adjustment_keys[adjustment.idempotency_key] = adjustment.adjustment_id

    def get_adjustment_by_key(self, idempotency_key: str) -> SpoolAdjustment | None:
        adjustment_id = self._adjustment_keys.get(idempotency_key)
        return None if adjustment_id is None else self._adjustments[adjustment_id]

    def list_adjustments(self, spool_id: UUID) -> tuple[SpoolAdjustment, ...]:
        return tuple(
            sorted(
                (adjustment for adjustment in self._adjustments.values() if adjustment.spool_id == spool_id),
                key=lambda adjustment: (adjustment.created_at, str(adjustment.adjustment_id)),
            )
        )

    def save_assignment(self, assignment: SpoolAssignment) -> None:
        if assignment.spool_id not in self._spools:
            raise InventoryStoreMissingError(f"spool does not exist: {assignment.spool_id}")

        previous = self._assignments_by_spool.get(assignment.spool_id)
        if previous is not None:
            self._assignments_by_slot.pop((previous.printer_id, previous.slot_id), None)

        slot_key = (assignment.printer_id, assignment.slot_id)
        other_spool_id = self._assignments_by_slot.get(slot_key)
        if other_spool_id is not None and other_spool_id != assignment.spool_id:
            raise InventoryStoreConflictError(f"material slot already assigned: {assignment.printer_id}/{assignment.slot_id}")

        self._assignments_by_spool[assignment.spool_id] = assignment
        self._assignments_by_slot[slot_key] = assignment.spool_id

    def delete_assignment(self, spool_id: UUID) -> None:
        assignment = self._assignments_by_spool.pop(spool_id, None)
        if assignment is not None:
            self._assignments_by_slot.pop((assignment.printer_id, assignment.slot_id), None)

    def assignment_for_spool(self, spool_id: UUID) -> SpoolAssignment | None:
        return self._assignments_by_spool.get(spool_id)

    def assignment_for_slot(self, printer_id: str, slot_id: str) -> SpoolAssignment | None:
        spool_id = self._assignments_by_slot.get((printer_id, slot_id))
        return None if spool_id is None else self._assignments_by_spool[spool_id]

    def list_assignments(self) -> tuple[SpoolAssignment, ...]:
        return tuple(
            sorted(
                self._assignments_by_spool.values(),
                key=lambda assignment: (assignment.printer_id, assignment.slot_id, str(assignment.spool_id)),
            )
        )
