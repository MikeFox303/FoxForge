# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace

from foxforge.adapters.moonraker.mapping import map_moonraker_material_system, map_moonraker_state
from foxforge.domain.printers import ConnectionState, JobState, OperationalState, utc_now


def test_offline_state_maps_to_common_offline_snapshot(moonraker_idle_state) -> None:
    snapshot = map_moonraker_state("printer-1", moonraker_idle_state)

    assert snapshot.connection == ConnectionState.DISCONNECTED
    assert snapshot.operational_state == OperationalState.OFFLINE
    assert snapshot.active_job is None


def test_printing_state_maps_progress_and_elapsed_time(moonraker_idle_state) -> None:
    native = replace(
        moonraker_idle_state,
        connected=True,
        print_state="printing",
        filename="part.gcode",
        progress=0.25,
        print_duration_seconds=12.8,
        observed_at=utc_now(),
    )
    snapshot = map_moonraker_state("printer-1", native)

    assert snapshot.connection == ConnectionState.CONNECTED
    assert snapshot.operational_state == OperationalState.PRINTING
    assert snapshot.active_job is not None
    assert snapshot.active_job.state == JobState.PRINTING
    assert snapshot.active_job.progress == 0.25
    assert snapshot.active_job.elapsed_seconds == 12


def test_klippy_shutdown_maps_to_degraded_failed_snapshot(moonraker_idle_state) -> None:
    native = replace(
        moonraker_idle_state,
        connected=True,
        klippy_state="shutdown",
        klippy_message="MCU shutdown",
        observed_at=utc_now(),
    )
    snapshot = map_moonraker_state("printer-1", native)

    assert snapshot.connection == ConnectionState.DEGRADED
    assert snapshot.operational_state == OperationalState.FAILED
    assert snapshot.fault_summary[0].code == "moonraker.klippy.shutdown"


def test_material_system_exposes_one_stable_external_slot(moonraker_idle_state) -> None:
    snapshot = map_moonraker_material_system("printer-1", moonraker_idle_state)

    assert len(snapshot.units) == 1
    assert len(snapshot.units[0].slots) == 1
    assert snapshot.units[0].slots[0].slot_id == "moonraker:external:0:slot:0"
    assert snapshot.stale is True
