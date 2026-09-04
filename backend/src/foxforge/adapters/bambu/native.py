# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Bambu-native transport DTOs.

This is newly written FoxForge code. The field choices are informed by public
Bambu/Bambuddy behavior, but vendor-native values stay inside this package and
are mapped into FoxForge domain contracts by the adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from foxforge.domain.printers.models import normalize_utc


class BambuMaterialUnitKind(StrEnum):
    AMS = "ams"
    AMS_2_PRO = "ams_2_pro"
    AMS_HT = "ams_ht"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class BambuNativeJobControlAction(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class BambuNativeFault:
    code: str
    severity: str
    message: str | None = None


@dataclass(frozen=True, slots=True)
class BambuNativeTray:
    ams_id: int
    tray_id: int
    material_type: str | None = None
    vendor_name: str | None = None
    product_name: str | None = None
    color_rgba: str | None = None
    tag_uid: str | None = None
    remaining_percent: int | None = None
    exists: bool | None = None
    active: bool | None = None


@dataclass(frozen=True, slots=True)
class BambuNativeMaterialUnit:
    ams_id: int
    kind: BambuMaterialUnitKind
    label: str | None
    trays: tuple[BambuNativeTray, ...]

    def __post_init__(self) -> None:
        if any(tray.ams_id != self.ams_id for tray in self.trays):
            raise ValueError("every Bambu tray must belong to its containing AMS unit")


@dataclass(frozen=True, slots=True)
class BambuNativeState:
    connected: bool
    gcode_state: str | None
    current_print: str | None
    vendor_job_id: str | None
    progress_percent: int | None
    remaining_minutes: int | None
    layer_num: int | None
    total_layers: int | None
    faults: tuple[BambuNativeFault, ...]
    material_units: tuple[BambuNativeMaterialUnit, ...]
    observed_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", normalize_utc(self.observed_at, field_name="observed_at"))


@dataclass(frozen=True, slots=True)
class BambuNativeMaterialRoute:
    material_index: int
    ams_id: int
    tray_id: int


@dataclass(frozen=True, slots=True)
class BambuNativePrintRequest:
    local_path: Path
    filename: str
    plate_number: int | None
    material_routes: tuple[BambuNativeMaterialRoute, ...]
    requested_name: str | None


@dataclass(frozen=True, slots=True)
class BambuNativeDispatchResult:
    accepted_at: datetime
    vendor_job_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "accepted_at", normalize_utc(self.accepted_at, field_name="accepted_at"))


@dataclass(frozen=True, slots=True)
class BambuNativeJobControlResult:
    accepted_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "accepted_at", normalize_utc(self.accepted_at, field_name="accepted_at"))
