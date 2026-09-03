# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Map Moonraker/Klipper-native state into vendor-neutral FoxForge contracts."""

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
    MaterialActivity,
    MaterialPresence,
    MaterialSlotSnapshot,
    MaterialSystemSnapshot,
    MaterialUnitKind,
    MaterialUnitSnapshot,
)

from .native import MoonrakerNativeState

MOONRAKER_EXTERNAL_UNIT_ID = "moonraker:external:0"
MOONRAKER_EXTERNAL_SLOT_ID = "moonraker:external:0:slot:0"

_PRINT_OPERATIONAL_STATES = {
    "standby": OperationalState.IDLE,
    "printing": OperationalState.PRINTING,
    "paused": OperationalState.PAUSED,
    "complete": OperationalState.COMPLETED,
    "error": OperationalState.FAILED,
    "cancelled": OperationalState.IDLE,
}

_PRINT_JOB_STATES = {
    "printing": JobState.PRINTING,
    "paused": JobState.PAUSED,
    "complete": JobState.COMPLETED,
    "error": JobState.FAILED,
    "cancelled": JobState.CANCELLED,
}


def map_moonraker_state(printer_id: PrinterId, native: MoonrakerNativeState) -> PrinterSnapshot:
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

    klippy_state = native.klippy_state.strip().lower()
    print_state = (native.print_state or "").strip().lower()
    if klippy_state == "ready":
        connection = ConnectionState.CONNECTED
        operational = _PRINT_OPERATIONAL_STATES.get(print_state, OperationalState.UNKNOWN)
    else:
        connection = ConnectionState.DEGRADED
        if klippy_state in {"startup", "initializing"}:
            operational = OperationalState.PREPARING
        elif klippy_state in {"shutdown", "error"}:
            operational = OperationalState.FAILED
        else:
            operational = OperationalState.UNKNOWN

    return PrinterSnapshot(
        printer_id=printer_id,
        connection=connection,
        operational_state=operational,
        active_job=_map_active_job(native, print_state),
        observed_at=native.observed_at,
        stale=False,
        fault_summary=_map_faults(native),
    )


def map_moonraker_material_system(printer_id: PrinterId, native: MoonrakerNativeState) -> MaterialSystemSnapshot:
    slot = MaterialSlotSnapshot(
        slot_id=MOONRAKER_EXTERNAL_SLOT_ID,
        unit_id=MOONRAKER_EXTERNAL_UNIT_ID,
        position=0,
        label="External spool",
        presence=MaterialPresence.UNKNOWN,
        activity=MaterialActivity.UNKNOWN,
        detected_material=None,
    )
    unit = MaterialUnitSnapshot(
        unit_id=MOONRAKER_EXTERNAL_UNIT_ID,
        kind=MaterialUnitKind.EXTERNAL,
        label="External spool",
        position=0,
        slots=(slot,),
    )
    return MaterialSystemSnapshot(
        printer_id=printer_id,
        units=(unit,),
        observed_at=native.observed_at,
        stale=not native.connected,
    )


def _map_active_job(native: MoonrakerNativeState, print_state: str) -> ActiveJobSnapshot | None:
    state = _PRINT_JOB_STATES.get(print_state)
    if state is None:
        return None
    elapsed = None
    if native.print_duration_seconds is not None:
        elapsed = int(native.print_duration_seconds)
    return ActiveJobSnapshot(
        vendor_job_id=native.filename,
        name=native.filename,
        state=state,
        progress=native.progress,
        elapsed_seconds=elapsed,
        remaining_seconds=None,
        current_layer=None,
        total_layers=None,
    )


def _map_faults(native: MoonrakerNativeState) -> tuple[PrinterFaultSummary, ...]:
    faults: list[PrinterFaultSummary] = []
    klippy_state = native.klippy_state.strip().lower()
    if klippy_state in {"shutdown", "error"}:
        severity = "critical" if klippy_state == "shutdown" else "error"
        faults.append(
            PrinterFaultSummary(
                code=f"moonraker.klippy.{klippy_state}",
                severity=severity,
                message=native.klippy_message,
            )
        )
    if (native.print_state or "").strip().lower() == "error":
        faults.append(
            PrinterFaultSummary(
                code="moonraker.print.error",
                severity="error",
                message=native.print_message,
            )
        )
    return tuple(faults)
