# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from typing import Protocol

from ..models import CapabilityDescriptor, PrinterId, normalize_utc

THERMAL_TELEMETRY_CAPABILITY_ID = "foxforge.thermal_telemetry"
THERMAL_TELEMETRY_MAJOR_VERSION = 1


class ThermalZoneKind(StrEnum):
    HOTEND = "hotend"
    BED = "bed"
    CHAMBER = "chamber"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ThermalTelemetryDescriptor(CapabilityDescriptor):
    reports_targets: bool

    def __post_init__(self) -> None:
        CapabilityDescriptor.__post_init__(self)
        if self.capability_id != THERMAL_TELEMETRY_CAPABILITY_ID or self.major_version != THERMAL_TELEMETRY_MAJOR_VERSION:
            raise ValueError("ThermalTelemetryDescriptor must describe foxforge.thermal_telemetry v1")


@dataclass(frozen=True, slots=True)
class ThermalZoneSnapshot:
    zone_id: str
    kind: ThermalZoneKind
    position: int
    label: str | None
    current_celsius: float | None
    target_celsius: float | None

    def __post_init__(self) -> None:
        if not self.zone_id:
            raise ValueError("zone_id must not be empty")
        if self.position < 0:
            raise ValueError("thermal zone position must be non-negative")
        if self.current_celsius is None and self.target_celsius is None:
            raise ValueError("thermal zone must report current_celsius or target_celsius")
        for field_name in ("current_celsius", "target_celsius"):
            value = getattr(self, field_name)
            if value is not None and not isfinite(value):
                raise ValueError(f"{field_name} must be finite when present")


@dataclass(frozen=True, slots=True)
class ThermalTelemetrySnapshot:
    printer_id: PrinterId
    zones: tuple[ThermalZoneSnapshot, ...]
    observed_at: datetime
    stale: bool

    def __post_init__(self) -> None:
        if not self.printer_id:
            raise ValueError("printer_id must not be empty")
        zone_ids = [zone.zone_id for zone in self.zones]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("thermal zone ids must be unique")
        object.__setattr__(self, "observed_at", normalize_utc(self.observed_at, field_name="observed_at"))


class ThermalTelemetryCapability(Protocol):
    @property
    def descriptor(self) -> ThermalTelemetryDescriptor: ...

    def snapshot(self) -> ThermalTelemetrySnapshot: ...
