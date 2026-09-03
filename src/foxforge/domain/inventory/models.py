# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from foxforge.domain.printers.models import normalize_utc


class SpoolAdjustmentKind(StrEnum):
    CONSUMPTION = "consumption"
    CORRECTION = "correction"
    RETURN = "return"
    WASTE = "waste"


@dataclass(frozen=True, slots=True)
class SpoolColor:
    rgba_hex: str

    def __post_init__(self) -> None:
        value = self.rgba_hex.strip().upper()
        if len(value) not in {6, 8} or any(character not in "0123456789ABCDEF" for character in value):
            raise ValueError("rgba_hex must contain 6 or 8 hexadecimal characters")
        object.__setattr__(self, "rgba_hex", value)


@dataclass(frozen=True, slots=True)
class Spool:
    spool_id: UUID
    material_family: str
    initial_filament_mass_g: Decimal
    manufacturer: str | None
    product_name: str | None
    color: SpoolColor | None
    empty_spool_mass_g: Decimal | None
    purchase_date: date | None
    created_at: datetime
    updated_at: datetime
    archived: bool = False

    def __post_init__(self) -> None:
        material_family = self.material_family.strip()
        if not material_family:
            raise ValueError("material_family must not be empty")
        object.__setattr__(self, "material_family", material_family)
        object.__setattr__(self, "manufacturer", _optional_text(self.manufacturer))
        object.__setattr__(self, "product_name", _optional_text(self.product_name))
        object.__setattr__(
            self,
            "initial_filament_mass_g",
            _positive_mass(self.initial_filament_mass_g, field_name="initial_filament_mass_g"),
        )
        if self.empty_spool_mass_g is not None:
            object.__setattr__(
                self,
                "empty_spool_mass_g",
                _nonnegative_mass(self.empty_spool_mass_g, field_name="empty_spool_mass_g"),
            )
        object.__setattr__(self, "created_at", normalize_utc(self.created_at, field_name="created_at"))
        object.__setattr__(self, "updated_at", normalize_utc(self.updated_at, field_name="updated_at"))
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")


@dataclass(frozen=True, slots=True)
class SpoolAdjustment:
    adjustment_id: UUID
    spool_id: UUID
    kind: SpoolAdjustmentKind
    delta_filament_mass_g: Decimal
    idempotency_key: str
    created_at: datetime
    note: str | None = None

    def __post_init__(self) -> None:
        delta = _finite_decimal(self.delta_filament_mass_g, field_name="delta_filament_mass_g")
        if delta == 0:
            raise ValueError("delta_filament_mass_g must not be zero")
        if self.kind in {SpoolAdjustmentKind.CONSUMPTION, SpoolAdjustmentKind.WASTE} and delta >= 0:
            raise ValueError(f"{self.kind.value} adjustments must decrease filament mass")
        if self.kind == SpoolAdjustmentKind.RETURN and delta <= 0:
            raise ValueError("return adjustments must increase filament mass")
        key = self.idempotency_key.strip()
        if not key:
            raise ValueError("idempotency_key must not be empty")
        object.__setattr__(self, "delta_filament_mass_g", delta)
        object.__setattr__(self, "idempotency_key", key)
        object.__setattr__(self, "note", _optional_text(self.note))
        object.__setattr__(self, "created_at", normalize_utc(self.created_at, field_name="created_at"))


@dataclass(frozen=True, slots=True)
class SpoolBalance:
    spool_id: UUID
    initial_filament_mass_g: Decimal
    remaining_filament_mass_g: Decimal
    used_filament_mass_g: Decimal
    used_fraction: Decimal

    def __post_init__(self) -> None:
        initial = _positive_mass(self.initial_filament_mass_g, field_name="initial_filament_mass_g")
        remaining = _nonnegative_mass(self.remaining_filament_mass_g, field_name="remaining_filament_mass_g")
        used = _finite_decimal(self.used_filament_mass_g, field_name="used_filament_mass_g")
        fraction = _finite_decimal(self.used_fraction, field_name="used_fraction")
        if remaining > initial:
            raise ValueError("remaining_filament_mass_g must not exceed initial_filament_mass_g")
        if used != initial - remaining:
            raise ValueError("used_filament_mass_g must equal initial minus remaining")
        if fraction < 0 or fraction > 1:
            raise ValueError("used_fraction must be between 0 and 1")
        object.__setattr__(self, "initial_filament_mass_g", initial)
        object.__setattr__(self, "remaining_filament_mass_g", remaining)
        object.__setattr__(self, "used_filament_mass_g", used)
        object.__setattr__(self, "used_fraction", fraction)


@dataclass(frozen=True, slots=True)
class SpoolAssignment:
    spool_id: UUID
    printer_id: str
    slot_id: str
    assigned_at: datetime

    def __post_init__(self) -> None:
        printer_id = self.printer_id.strip()
        slot_id = self.slot_id.strip()
        if not printer_id or not slot_id:
            raise ValueError("printer_id and slot_id must not be empty")
        object.__setattr__(self, "printer_id", printer_id)
        object.__setattr__(self, "slot_id", slot_id)
        object.__setattr__(self, "assigned_at", normalize_utc(self.assigned_at, field_name="assigned_at"))


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _finite_decimal(value: Decimal, *, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be Decimal")
    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return value


def _nonnegative_mass(value: Decimal, *, field_name: str) -> Decimal:
    mass = _finite_decimal(value, field_name=field_name)
    if mass < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return mass


def _positive_mass(value: Decimal, *, field_name: str) -> Decimal:
    mass = _finite_decimal(value, field_name=field_name)
    if mass <= 0:
        raise ValueError(f"{field_name} must be positive")
    return mass
