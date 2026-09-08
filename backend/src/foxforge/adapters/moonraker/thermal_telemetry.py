# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Callable

from foxforge.domain.printers.capabilities import (
    THERMAL_TELEMETRY_CAPABILITY_ID,
    THERMAL_TELEMETRY_MAJOR_VERSION,
    ThermalTelemetryDescriptor,
    ThermalTelemetrySnapshot,
    ThermalZoneKind,
    ThermalZoneSnapshot,
)

from .native import MoonrakerNativeState, MoonrakerNativeThermalZone


class MoonrakerThermalTelemetryCapability:
    """Map discovered Klipper heater objects into the common thermal v1 contract."""

    def __init__(self, printer_id: str, native_state: Callable[[], MoonrakerNativeState]) -> None:
        self._printer_id = printer_id
        self._native_state = native_state
        self._descriptor = ThermalTelemetryDescriptor(
            capability_id=THERMAL_TELEMETRY_CAPABILITY_ID,
            major_version=THERMAL_TELEMETRY_MAJOR_VERSION,
            reports_targets=True,
        )

    @property
    def descriptor(self) -> ThermalTelemetryDescriptor:
        return self._descriptor

    def snapshot(self) -> ThermalTelemetrySnapshot:
        native = self._native_state()
        return ThermalTelemetrySnapshot(
            printer_id=self._printer_id,
            zones=tuple(_map_zone(zone) for zone in native.thermal_zones),
            observed_at=native.observed_at,
            stale=not native.connected,
        )


def _map_zone(zone: MoonrakerNativeThermalZone) -> ThermalZoneSnapshot:
    if zone.object_name == "heater_bed":
        zone_id = "bed:0"
        kind = ThermalZoneKind.BED
        label = "Bed"
    else:
        zone_id = f"hotend:{zone.position}"
        kind = ThermalZoneKind.HOTEND
        label = "Hotend" if zone.position == 0 else f"Hotend {zone.position + 1}"
    return ThermalZoneSnapshot(
        zone_id=zone_id,
        kind=kind,
        position=zone.position,
        label=label,
        current_celsius=zone.current_celsius,
        target_celsius=zone.target_celsius,
    )
