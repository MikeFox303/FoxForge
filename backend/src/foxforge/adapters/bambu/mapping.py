# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Map Bambu-native state into vendor-neutral FoxForge contracts."""

from __future__ import annotations

from foxforge.domain.printers import (
    ActiveJobSnapshot,
    ConnectionState,
    JobState,
    OperationalState,
    PrinterFaultSummary,
    PrinterId,
    PrinterSnapshot,
)
from foxforge.domain.printers.capabilities import (
    DetectedMaterial,
    MaterialActivity,
    MaterialColor,
    MaterialPresence,
    MaterialSlotSnapshot,
    MaterialSystemSnapshot,
    MaterialTagIdentity,
    MaterialUnitKind,
    MaterialUnitSnapshot,
)

from .native import BambuMaterialUnitKind, BambuNativeMaterialUnit, BambuNativeState, BambuNativeTray

_BAMBU_OPERATIONAL_STATES = {
    "IDLE": OperationalState.IDLE,
    "PREPARE": OperationalState.PREPARING,
    "SLICING": OperationalState.PREPARING,
    "RUNNING": OperationalState.PRINTING,
    "PAUSE": OperationalState.PAUSED,
    "FINISH": OperationalState.COMPLETED,
    "FAILED": OperationalState.FAILED,
}

_BAMBU_JOB_STATES = {
    "PREPARE": JobState.PREPARING,
    "SLICING": JobState.PREPARING,
    "RUNNING": JobState.PRINTING,
    "PAUSE": JobState.PAUSED,
    "FINISH": JobState.COMPLETED,
    "FAILED": JobState.FAILED,
}

_MATERIAL_UNIT_KIND = {
    BambuMaterialUnitKind.AMS: MaterialUnitKind.MULTI_SLOT,
    BambuMaterialUnitKind.AMS_2_PRO: MaterialUnitKind.MULTI_SLOT,
    BambuMaterialUnitKind.AMS_HT: MaterialUnitKind.MULTI_SLOT,
    BambuMaterialUnitKind.EXTERNAL: MaterialUnitKind.EXTERNAL,
    BambuMaterialUnitKind.UNKNOWN: MaterialUnitKind.OTHER,
}


def map_bambu_state(printer_id: PrinterId, native: BambuNativeState) -> PrinterSnapshot:
    if not native.connected:
        return PrinterSnapshot(
            printer_id=printer_id,
            connection=ConnectionState.DISCONNECTED,
            operational_state=OperationalState.OFFLINE,
            active_job=None,
            observed_at=native.observed_at,
            stale=False,
            fault_summary=_map_faults(native),
        )

    state_name = (native.gcode_state or "").strip().upper()
    operational_state = _BAMBU_OPERATIONAL_STATES.get(state_name, OperationalState.UNKNOWN)
    active_job = _map_active_job(native, state_name)

    return PrinterSnapshot(
        printer_id=printer_id,
        connection=ConnectionState.CONNECTED,
        operational_state=operational_state,
        active_job=active_job,
        observed_at=native.observed_at,
        stale=False,
        fault_summary=_map_faults(native),
    )


def map_bambu_material_system(printer_id: PrinterId, native: BambuNativeState) -> MaterialSystemSnapshot:
    return MaterialSystemSnapshot(
        printer_id=printer_id,
        units=tuple(_map_material_unit(unit) for unit in native.material_units),
        observed_at=native.observed_at,
        stale=not native.connected,
    )


def bambu_slot_id(ams_id: int, tray_id: int) -> str:
    return f"bambu:unit:{ams_id}:tray:{tray_id}"


def bambu_unit_id(ams_id: int) -> str:
    return f"bambu:unit:{ams_id}"


def bambu_slot_routes(native: BambuNativeState) -> dict[str, tuple[int, int]]:
    return {
        bambu_slot_id(tray.ams_id, tray.tray_id): (tray.ams_id, tray.tray_id)
        for unit in native.material_units
        for tray in unit.trays
    }


def _map_active_job(native: BambuNativeState, state_name: str) -> ActiveJobSnapshot | None:
    job_state = _BAMBU_JOB_STATES.get(state_name)
    if job_state is None:
        return None
    return ActiveJobSnapshot(
        vendor_job_id=native.vendor_job_id,
        name=native.current_print,
        state=job_state,
        progress=_percent_fraction(native.progress_percent),
        elapsed_seconds=None,
        remaining_seconds=_minutes_seconds(native.remaining_minutes),
        current_layer=_nonnegative(native.layer_num),
        total_layers=_nonnegative(native.total_layers),
    )


def _map_faults(native: BambuNativeState) -> tuple[PrinterFaultSummary, ...]:
    allowed = {"info", "warning", "error", "critical"}
    result: list[PrinterFaultSummary] = []
    for fault in native.faults:
        severity = fault.severity.strip().lower()
        if severity not in allowed:
            severity = "error"
        result.append(PrinterFaultSummary(code=fault.code, severity=severity, message=fault.message))  # type: ignore[arg-type]
    return tuple(result)


def _map_material_unit(unit: BambuNativeMaterialUnit) -> MaterialUnitSnapshot:
    unit_id = bambu_unit_id(unit.ams_id)
    return MaterialUnitSnapshot(
        unit_id=unit_id,
        kind=_MATERIAL_UNIT_KIND[unit.kind],
        label=unit.label,
        position=max(unit.ams_id, 0),
        slots=tuple(_map_tray(unit_id, tray) for tray in unit.trays),
    )


def _map_tray(unit_id: str, tray: BambuNativeTray) -> MaterialSlotSnapshot:
    return MaterialSlotSnapshot(
        slot_id=bambu_slot_id(tray.ams_id, tray.tray_id),
        unit_id=unit_id,
        position=max(tray.tray_id, 0),
        label=f"Tray {tray.tray_id + 1}" if tray.tray_id >= 0 else None,
        presence=_presence(tray.exists),
        activity=_activity(tray.active),
        detected_material=_detected_material(tray),
    )


def _detected_material(tray: BambuNativeTray) -> DetectedMaterial | None:
    has_identity = any(
        value
        for value in (
            tray.material_type,
            tray.vendor_name,
            tray.product_name,
            tray.color_rgba,
            tray.tag_uid,
        )
    )
    remaining = _percent_fraction(tray.remaining_percent)
    if not has_identity and remaining is None:
        return None
    color_value = (tray.color_rgba or "").strip().lstrip("#").upper()
    color = MaterialColor(color_value) if color_value else None
    tag = MaterialTagIdentity(scheme="bambu_tag_uid", value=tray.tag_uid) if tray.tag_uid else None
    return DetectedMaterial(
        material_family=tray.material_type,
        vendor_name=tray.vendor_name,
        product_name=tray.product_name,
        color=color,
        tag=tag,
        remaining_fraction=remaining,
    )


def _presence(value: bool | None) -> MaterialPresence:
    if value is True:
        return MaterialPresence.LOADED
    if value is False:
        return MaterialPresence.EMPTY
    return MaterialPresence.UNKNOWN


def _activity(value: bool | None) -> MaterialActivity:
    if value is True:
        return MaterialActivity.ACTIVE
    if value is False:
        return MaterialActivity.INACTIVE
    return MaterialActivity.UNKNOWN


def _percent_fraction(value: int | None) -> float | None:
    if value is None or not 0 <= value <= 100:
        return None
    return value / 100.0


def _minutes_seconds(value: int | None) -> int | None:
    if value is None or value < 0:
        return None
    return value * 60


def _nonnegative(value: int | None) -> int | None:
    if value is None or value < 0:
        return None
    return value
