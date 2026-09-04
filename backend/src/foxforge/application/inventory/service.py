# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from foxforge.domain.inventory import (
    Spool,
    SpoolAdjustment,
    SpoolAdjustmentKind,
    SpoolAssignment,
    SpoolBalance,
    SpoolColor,
)

from .store import InventoryStore, InventoryStoreConflictError


class SpoolNotFoundError(KeyError):
    pass


class ArchivedSpoolError(RuntimeError):
    pass


class InventoryIdempotencyConflictError(RuntimeError):
    pass


class InventoryBalanceError(ValueError):
    pass


class SpoolAssignmentConflictError(RuntimeError):
    pass


class InventoryService:
    """Application service for spool metadata, mass ledger, and physical assignment."""

    def __init__(self, store: InventoryStore) -> None:
        self._store = store

    def add_spool(
        self,
        *,
        material_family: str,
        initial_filament_mass_g: Decimal,
        manufacturer: str | None = None,
        product_name: str | None = None,
        color: SpoolColor | None = None,
        empty_spool_mass_g: Decimal | None = None,
        purchase_date: date | None = None,
        spool_id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> Spool:
        now = created_at or datetime.now(UTC)
        spool = Spool(
            spool_id=spool_id or uuid4(),
            material_family=material_family,
            initial_filament_mass_g=initial_filament_mass_g,
            manufacturer=manufacturer,
            product_name=product_name,
            color=color,
            empty_spool_mass_g=empty_spool_mass_g,
            purchase_date=purchase_date,
            created_at=now,
            updated_at=now,
        )
        self._store.create_spool(spool)
        return spool

    def get_spool(self, spool_id: UUID) -> Spool:
        spool = self._store.get_spool(spool_id)
        if spool is None:
            raise SpoolNotFoundError(str(spool_id))
        return spool

    def list_spools(self, *, include_archived: bool = False) -> tuple[Spool, ...]:
        spools = self._store.list_spools()
        if include_archived:
            return spools
        return tuple(spool for spool in spools if not spool.archived)

    def set_empty_spool_mass(self, spool_id: UUID, empty_spool_mass_g: Decimal | None) -> Spool:
        spool = self.get_spool(spool_id)
        updated = replace(spool, empty_spool_mass_g=empty_spool_mass_g, updated_at=datetime.now(UTC))
        self._store.save_spool(updated)
        return updated

    def archive_spool(self, spool_id: UUID) -> Spool:
        spool = self.get_spool(spool_id)
        if spool.archived:
            return spool
        if self._store.assignment_for_spool(spool_id) is not None:
            raise SpoolAssignmentConflictError("assigned spool must be unassigned before archiving")
        archived = replace(spool, archived=True, updated_at=datetime.now(UTC))
        self._store.save_spool(archived)
        return archived

    def balance(self, spool_id: UUID) -> SpoolBalance:
        spool = self.get_spool(spool_id)
        adjustment_total = sum(
            (adjustment.delta_filament_mass_g for adjustment in self._store.list_adjustments(spool_id)),
            start=Decimal("0"),
        )
        remaining = spool.initial_filament_mass_g + adjustment_total
        if remaining < 0 or remaining > spool.initial_filament_mass_g:
            raise InventoryBalanceError("stored adjustment ledger produces an invalid spool balance")
        used = spool.initial_filament_mass_g - remaining
        return SpoolBalance(
            spool_id=spool_id,
            initial_filament_mass_g=spool.initial_filament_mass_g,
            remaining_filament_mass_g=remaining,
            used_filament_mass_g=used,
            used_fraction=used / spool.initial_filament_mass_g,
        )

    def adjustments(self, spool_id: UUID) -> tuple[SpoolAdjustment, ...]:
        self.get_spool(spool_id)
        return self._store.list_adjustments(spool_id)

    def consume(
        self,
        spool_id: UUID,
        mass_g: Decimal,
        *,
        idempotency_key: str,
        note: str | None = None,
    ) -> SpoolAdjustment:
        mass = _positive_mass(mass_g, field_name="mass_g")
        return self._record_adjustment(
            spool_id,
            kind=SpoolAdjustmentKind.CONSUMPTION,
            delta=-mass,
            idempotency_key=idempotency_key,
            note=note,
        )

    def record_waste(
        self,
        spool_id: UUID,
        mass_g: Decimal,
        *,
        idempotency_key: str,
        note: str | None = None,
    ) -> SpoolAdjustment:
        mass = _positive_mass(mass_g, field_name="mass_g")
        return self._record_adjustment(
            spool_id,
            kind=SpoolAdjustmentKind.WASTE,
            delta=-mass,
            idempotency_key=idempotency_key,
            note=note,
        )

    def return_material(
        self,
        spool_id: UUID,
        mass_g: Decimal,
        *,
        idempotency_key: str,
        note: str | None = None,
    ) -> SpoolAdjustment:
        mass = _positive_mass(mass_g, field_name="mass_g")
        return self._record_adjustment(
            spool_id,
            kind=SpoolAdjustmentKind.RETURN,
            delta=mass,
            idempotency_key=idempotency_key,
            note=note,
        )

    def correct_by_delta(
        self,
        spool_id: UUID,
        delta_mass_g: Decimal,
        *,
        idempotency_key: str,
        note: str | None = None,
    ) -> SpoolAdjustment:
        delta = _nonzero_mass_delta(delta_mass_g, field_name="delta_mass_g")
        return self._record_adjustment(
            spool_id,
            kind=SpoolAdjustmentKind.CORRECTION,
            delta=delta,
            idempotency_key=idempotency_key,
            note=note,
        )

    def assign_spool(self, spool_id: UUID, printer_id: str, slot_id: str) -> SpoolAssignment:
        spool = self.get_spool(spool_id)
        if spool.archived:
            raise ArchivedSpoolError("archived spool cannot be assigned")

        existing = self._store.assignment_for_spool(spool_id)
        if existing is not None:
            if existing.printer_id == printer_id.strip() and existing.slot_id == slot_id.strip():
                return existing
            raise SpoolAssignmentConflictError("spool is already assigned; use move_spool to change slots")

        occupied = self._store.assignment_for_slot(printer_id.strip(), slot_id.strip())
        if occupied is not None and occupied.spool_id != spool_id:
            raise SpoolAssignmentConflictError("material slot already has another spool assigned")

        assignment = SpoolAssignment(
            spool_id=spool_id,
            printer_id=printer_id,
            slot_id=slot_id,
            assigned_at=datetime.now(UTC),
        )
        try:
            self._store.save_assignment(assignment)
        except InventoryStoreConflictError as error:
            raise SpoolAssignmentConflictError(str(error)) from error
        return assignment

    def move_spool(self, spool_id: UUID, printer_id: str, slot_id: str) -> SpoolAssignment:
        """Atomically assign or move a spool to one physical material slot.

        InventoryStore.save_assignment is the transaction boundary. SQLite uses
        one upsert transaction, so a move never passes through a durable
        unassigned intermediate state.
        """

        spool = self.get_spool(spool_id)
        if spool.archived:
            raise ArchivedSpoolError("archived spool cannot be assigned")

        target_printer = printer_id.strip()
        target_slot = slot_id.strip()
        existing = self._store.assignment_for_spool(spool_id)
        if existing is not None and existing.printer_id == target_printer and existing.slot_id == target_slot:
            return existing

        occupied = self._store.assignment_for_slot(target_printer, target_slot)
        if occupied is not None and occupied.spool_id != spool_id:
            raise SpoolAssignmentConflictError("material slot already has another spool assigned")

        assignment = SpoolAssignment(
            spool_id=spool_id,
            printer_id=target_printer,
            slot_id=target_slot,
            assigned_at=datetime.now(UTC),
        )
        try:
            self._store.save_assignment(assignment)
        except InventoryStoreConflictError as error:
            raise SpoolAssignmentConflictError(str(error)) from error
        return assignment

    def unassign_spool(self, spool_id: UUID) -> SpoolAssignment | None:
        self.get_spool(spool_id)
        assignment = self._store.assignment_for_spool(spool_id)
        self._store.delete_assignment(spool_id)
        return assignment

    def assignment_for_spool(self, spool_id: UUID) -> SpoolAssignment | None:
        self.get_spool(spool_id)
        return self._store.assignment_for_spool(spool_id)

    def assignment_for_slot(self, printer_id: str, slot_id: str) -> SpoolAssignment | None:
        return self._store.assignment_for_slot(printer_id.strip(), slot_id.strip())

    def assignments(self) -> tuple[SpoolAssignment, ...]:
        return self._store.list_assignments()

    def _record_adjustment(
        self,
        spool_id: UUID,
        *,
        kind: SpoolAdjustmentKind,
        delta: Decimal,
        idempotency_key: str,
        note: str | None,
    ) -> SpoolAdjustment:
        spool = self.get_spool(spool_id)
        key = idempotency_key.strip()
        if not key:
            raise ValueError("idempotency_key must not be empty")

        existing = self._store.get_adjustment_by_key(key)
        if existing is not None:
            if (
                existing.spool_id == spool_id
                and existing.kind == kind
                and existing.delta_filament_mass_g == delta
                and existing.note == _optional_text(note)
            ):
                return existing
            raise InventoryIdempotencyConflictError(f"idempotency key already used with different data: {key}")

        if spool.archived:
            raise ArchivedSpoolError("archived spool cannot receive new mass adjustments")

        current = self.balance(spool_id).remaining_filament_mass_g
        next_remaining = current + delta
        if next_remaining < 0:
            raise InventoryBalanceError("adjustment would make remaining filament negative")
        if next_remaining > spool.initial_filament_mass_g:
            raise InventoryBalanceError("adjustment would exceed initial filament mass")

        adjustment = SpoolAdjustment(
            adjustment_id=uuid4(),
            spool_id=spool_id,
            kind=kind,
            delta_filament_mass_g=delta,
            idempotency_key=key,
            created_at=datetime.now(UTC),
            note=note,
        )
        self._store.append_adjustment(adjustment)
        return adjustment


def _finite_decimal(value: Decimal, *, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be Decimal")
    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return value


def _positive_mass(value: Decimal, *, field_name: str) -> Decimal:
    mass = _finite_decimal(value, field_name=field_name)
    if mass <= 0:
        raise ValueError(f"{field_name} must be positive")
    return mass


def _nonzero_mass_delta(value: Decimal, *, field_name: str) -> Decimal:
    delta = _finite_decimal(value, field_name=field_name)
    if delta == 0:
        raise ValueError(f"{field_name} must not be zero")
    return delta


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
