# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from ..models import (
    CapabilityDescriptor,
    MaterialSlotId,
    MaterialUnitId,
    PrinterId,
    normalize_utc,
    validate_fraction,
)

MATERIAL_SYSTEM_CAPABILITY_ID = "foxforge.material_system"
MATERIAL_SYSTEM_MAJOR_VERSION = 1


@dataclass(frozen=True, slots=True)
class MaterialSystemDescriptor(CapabilityDescriptor):
    reports_active_source: bool
    reports_remaining_fraction: bool
    reports_material_identity: bool
    reports_tag_identity: bool

    def __post_init__(self) -> None:
        CapabilityDescriptor.__post_init__(self)
        if self.capability_id != MATERIAL_SYSTEM_CAPABILITY_ID or self.major_version != MATERIAL_SYSTEM_MAJOR_VERSION:
            raise ValueError("MaterialSystemDescriptor must describe foxforge.material_system v1")


class MaterialUnitKind(StrEnum):
    MULTI_SLOT = "multi_slot"
    EXTERNAL = "external"
    TOOLHEAD = "toolhead"
    OTHER = "other"


class MaterialPresence(StrEnum):
    EMPTY = "empty"
    LOADED = "loaded"
    UNKNOWN = "unknown"


class MaterialActivity(StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MaterialColor:
    rgba_hex: str

    def __post_init__(self) -> None:
        if not self.rgba_hex:
            raise ValueError("rgba_hex must not be empty")


@dataclass(frozen=True, slots=True)
class MaterialTagIdentity:
    scheme: str
    value: str

    def __post_init__(self) -> None:
        if not self.scheme or not self.value:
            raise ValueError("material tag scheme and value must not be empty")


@dataclass(frozen=True, slots=True)
class DetectedMaterial:
    material_family: str | None
    vendor_name: str | None
    product_name: str | None
    color: MaterialColor | None
    tag: MaterialTagIdentity | None
    remaining_fraction: float | None

    def __post_init__(self) -> None:
        validate_fraction(self.remaining_fraction, field_name="remaining_fraction")


@dataclass(frozen=True, slots=True)
class MaterialSlotSnapshot:
    slot_id: MaterialSlotId
    unit_id: MaterialUnitId
    position: int
    label: str | None
    presence: MaterialPresence
    activity: MaterialActivity
    detected_material: DetectedMaterial | None

    def __post_init__(self) -> None:
        if not self.slot_id or not self.unit_id:
            raise ValueError("slot_id and unit_id must not be empty")
        if self.position < 0:
            raise ValueError("slot position must be non-negative")


@dataclass(frozen=True, slots=True)
class MaterialUnitSnapshot:
    unit_id: MaterialUnitId
    kind: MaterialUnitKind
    label: str | None
    position: int
    slots: tuple[MaterialSlotSnapshot, ...]

    def __post_init__(self) -> None:
        if not self.unit_id:
            raise ValueError("unit_id must not be empty")
        if self.position < 0:
            raise ValueError("unit position must be non-negative")
        slot_ids = [slot.slot_id for slot in self.slots]
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("slot ids must be unique within a material unit")
        if any(slot.unit_id != self.unit_id for slot in self.slots):
            raise ValueError("every slot unit_id must match its containing unit")


@dataclass(frozen=True, slots=True)
class MaterialSystemSnapshot:
    printer_id: PrinterId
    units: tuple[MaterialUnitSnapshot, ...]
    observed_at: datetime
    stale: bool

    def __post_init__(self) -> None:
        if not self.printer_id:
            raise ValueError("printer_id must not be empty")
        unit_ids = [unit.unit_id for unit in self.units]
        if len(unit_ids) != len(set(unit_ids)):
            raise ValueError("material unit ids must be unique")
        all_slot_ids = [slot.slot_id for unit in self.units for slot in unit.slots]
        if len(all_slot_ids) != len(set(all_slot_ids)):
            raise ValueError("material slot ids must be unique across the printer")
        object.__setattr__(self, "observed_at", normalize_utc(self.observed_at, field_name="observed_at"))


class MaterialSystemCapability(Protocol):
    @property
    def descriptor(self) -> MaterialSystemDescriptor: ...

    def snapshot(self) -> MaterialSystemSnapshot: ...
