# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from pathlib import Path

from foxforge.domain.printers.models import normalize_utc, validate_fraction


class MoonrakerNativeJobControlAction(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class MoonrakerNativeThermalZone:
    """Moonraker/Klipper thermal object retained inside the adapter boundary."""

    object_name: str
    position: int
    current_celsius: float | None
    target_celsius: float | None

    def __post_init__(self) -> None:
        if not self.object_name:
            raise ValueError("object_name must not be empty")
        if self.position < 0:
            raise ValueError("thermal zone position must be non-negative")
        if self.current_celsius is None and self.target_celsius is None:
            raise ValueError("thermal zone must report a current or target temperature")
        for field_name in ("current_celsius", "target_celsius"):
            value = getattr(self, field_name)
            if value is not None and not isfinite(value):
                raise ValueError(f"{field_name} must be finite when present")


@dataclass(frozen=True, slots=True)
class MoonrakerNativeState:
    """Vendor-native Moonraker/Klipper state kept inside the adapter package."""

    connected: bool
    klippy_state: str
    klippy_message: str | None
    print_state: str | None
    filename: str | None
    progress: float | None
    print_duration_seconds: float | None
    print_message: str | None
    observed_at: datetime
    thermal_zones: tuple[MoonrakerNativeThermalZone, ...] = ()

    def __post_init__(self) -> None:
        if not self.klippy_state:
            raise ValueError("klippy_state must not be empty")
        validate_fraction(self.progress, field_name="progress")
        if self.print_duration_seconds is not None and self.print_duration_seconds < 0:
            raise ValueError("print_duration_seconds must be non-negative")
        zone_names = [zone.object_name for zone in self.thermal_zones]
        if len(zone_names) != len(set(zone_names)):
            raise ValueError("thermal object names must be unique")
        object.__setattr__(self, "observed_at", normalize_utc(self.observed_at, field_name="observed_at"))


@dataclass(frozen=True, slots=True)
class MoonrakerNativePrintRequest:
    local_path: Path
    filename: str
    sha256: str

    def __post_init__(self) -> None:
        if not self.filename:
            raise ValueError("filename must not be empty")
        if len(self.sha256) != 64:
            raise ValueError("sha256 must contain 64 hex characters")
        try:
            int(self.sha256, 16)
        except ValueError as error:
            raise ValueError("sha256 must be hexadecimal") from error


@dataclass(frozen=True, slots=True)
class MoonrakerNativeDispatchResult:
    accepted_at: datetime
    vendor_job_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "accepted_at", normalize_utc(self.accepted_at, field_name="accepted_at"))


@dataclass(frozen=True, slots=True)
class MoonrakerNativeJobControlResult:
    accepted_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "accepted_at", normalize_utc(self.accepted_at, field_name="accepted_at"))
