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

from .native import BambuNativeState, BambuNativeThermalZone


class BambuThermalTelemetryCapability:
    def __init__(self, printer_id: str, native_state: Callable[[], BambuNativeState]) -> None:
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


def _map_zone(zone: BambuNativeThermalZone) -> ThermalZoneSnapshot:
    common_id, kind, label = _zone_identity(zone.zone_id)
    return ThermalZoneSnapshot(
        zone_id=common_id,
        kind=kind,
        position=zone.position,
        label=label,
        current_celsius=zone.current_celsius,
        target_celsius=zone.target_celsius,
    )


def _zone_identity(zone_id: str) -> tuple[str, ThermalZoneKind, str | None]:
    if zone_id == "hotend:right":
        return "hotend:0", ThermalZoneKind.HOTEND, "Right hotend"
    if zone_id == "hotend:left":
        return "hotend:1", ThermalZoneKind.HOTEND, "Left hotend"
    if zone_id == "hotend:0":
        return "hotend:0", ThermalZoneKind.HOTEND, "Hotend"
    if zone_id == "hotend:1":
        return "hotend:1", ThermalZoneKind.HOTEND, "Hotend 2"
    if zone_id == "bed":
        return "bed:0", ThermalZoneKind.BED, "Bed"
    if zone_id == "chamber":
        return "chamber:0", ThermalZoneKind.CHAMBER, "Chamber"
    return f"other:{zone_id}", ThermalZoneKind.OTHER, None
