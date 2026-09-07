# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from foxforge.domain.printers.models import normalize_utc


class FilamentReservationState(StrEnum):
    RESERVED = "reserved"
    CONSUMED = "consumed"
    RELEASED = "released"
    RECONCILIATION_REQUIRED = "reconciliation_required"


@dataclass(frozen=True, slots=True)
class MaterialEstimate:
    material_index: int
    estimated_mass_g: Decimal

    def __post_init__(self) -> None:
        if self.material_index < 0:
            raise ValueError("material_index must be zero-based and non-negative")
        if not isinstance(self.estimated_mass_g, Decimal) or not self.estimated_mass_g.is_finite():
            raise TypeError("estimated_mass_g must be a finite Decimal")
        if self.estimated_mass_g <= 0:
            raise ValueError("estimated_mass_g must be positive")


@dataclass(frozen=True, slots=True)
class FilamentReservation:
    queue_id: UUID
    material_index: int
    spool_id: UUID
    printer_id: str
    slot_id: str
    estimated_mass_g: Decimal
    state: FilamentReservationState
    created_at: datetime
    updated_at: datetime
    actual_mass_g: Decimal | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.material_index < 0:
            raise ValueError("material_index must be zero-based and non-negative")
        if not self.printer_id.strip() or not self.slot_id.strip():
            raise ValueError("printer_id and slot_id must not be empty")
        if not isinstance(self.estimated_mass_g, Decimal) or not self.estimated_mass_g.is_finite():
            raise TypeError("estimated_mass_g must be a finite Decimal")
        if self.estimated_mass_g <= 0:
            raise ValueError("estimated_mass_g must be positive")
        if self.actual_mass_g is not None:
            if not isinstance(self.actual_mass_g, Decimal) or not self.actual_mass_g.is_finite():
                raise TypeError("actual_mass_g must be a finite Decimal")
            if self.actual_mass_g < 0:
                raise ValueError("actual_mass_g must be non-negative")
        object.__setattr__(self, "printer_id", self.printer_id.strip())
        object.__setattr__(self, "slot_id", self.slot_id.strip())
        object.__setattr__(self, "created_at", normalize_utc(self.created_at, field_name="created_at"))
        object.__setattr__(self, "updated_at", normalize_utc(self.updated_at, field_name="updated_at"))
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.state == FilamentReservationState.CONSUMED and self.actual_mass_g is None:
            raise ValueError("consumed reservations require actual_mass_g")
        if self.state == FilamentReservationState.RELEASED and self.actual_mass_g not in {None, Decimal("0")}:
            raise ValueError("released reservations cannot contain positive actual mass")

    @property
    def holds_capacity(self) -> bool:
        return self.state in {
            FilamentReservationState.RESERVED,
            FilamentReservationState.RECONCILIATION_REQUIRED,
        }
