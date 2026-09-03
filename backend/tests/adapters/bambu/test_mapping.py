# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace

from foxforge.adapters.bambu.mapping import bambu_slot_id, map_bambu_material_system, map_bambu_state
from foxforge.domain.printers import ConnectionState, JobState, OperationalState, utc_now
from foxforge.domain.printers.capabilities import MaterialActivity, MaterialPresence, MaterialUnitKind


def test_running_state_maps_to_vendor_neutral_job(bambu_idle_state) -> None:
    native = replace(
        bambu_idle_state,
        connected=True,
        gcode_state="RUNNING",
        current_print="part.3mf",
        vendor_job_id="subtask-42",
        progress_percent=42,
        remaining_minutes=12,
        layer_num=21,
        total_layers=100,
        observed_at=utc_now(),
    )

    snapshot = map_bambu_state("bambu-1", native)

    assert snapshot.connection == ConnectionState.CONNECTED
    assert snapshot.operational_state == OperationalState.PRINTING
    assert snapshot.active_job is not None
    assert snapshot.active_job.state == JobState.PRINTING
    assert snapshot.active_job.progress == 0.42
    assert snapshot.active_job.remaining_seconds == 720
    assert snapshot.active_job.current_layer == 21
    assert snapshot.active_job.total_layers == 100


def test_disconnected_state_maps_offline_and_drops_active_job(bambu_idle_state) -> None:
    native = replace(
        bambu_idle_state,
        connected=False,
        gcode_state="RUNNING",
        current_print="part.3mf",
        progress_percent=50,
        observed_at=utc_now(),
    )

    snapshot = map_bambu_state("bambu-1", native)

    assert snapshot.connection == ConnectionState.DISCONNECTED
    assert snapshot.operational_state == OperationalState.OFFLINE
    assert snapshot.active_job is None


def test_unknown_or_sentinel_values_do_not_leak_into_common_domain(bambu_idle_state) -> None:
    native = replace(
        bambu_idle_state,
        connected=True,
        gcode_state="RUNNING",
        current_print="part.3mf",
        progress_percent=-1,
        remaining_minutes=-1,
        layer_num=-1,
        total_layers=-1,
        observed_at=utc_now(),
    )

    job = map_bambu_state("bambu-1", native).active_job

    assert job is not None
    assert job.progress is None
    assert job.remaining_seconds is None
    assert job.current_layer is None
    assert job.total_layers is None


def test_ams_2_pro_maps_to_common_material_slots_without_ams_types(bambu_idle_state) -> None:
    snapshot = map_bambu_material_system("bambu-1", bambu_idle_state)

    assert len(snapshot.units) == 1
    unit = snapshot.units[0]
    assert unit.kind == MaterialUnitKind.MULTI_SLOT
    assert unit.unit_id == "bambu:unit:0"
    assert unit.slots[0].slot_id == bambu_slot_id(0, 0)
    assert unit.slots[0].presence == MaterialPresence.LOADED
    assert unit.slots[0].activity == MaterialActivity.INACTIVE
    assert unit.slots[0].detected_material is not None
    assert unit.slots[0].detected_material.material_family == "PETG"
    assert unit.slots[0].detected_material.remaining_fraction == 0.8
    assert unit.slots[0].detected_material.color is not None
    assert unit.slots[0].detected_material.color.rgba_hex == "FF6600FF"
    assert unit.slots[0].detected_material.tag is not None
    assert unit.slots[0].detected_material.tag.scheme == "bambu_tag_uid"
