# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace

from foxforge.adapters.bambu import BambuAdapter
from foxforge.adapters.bambu.native import BambuNativeThermalZone
from foxforge.adapters.bambu.thermal_codec import BambuThermalCodec
from foxforge.api.v1.read_models import fleet_read_model
from foxforge.application.fleet import FleetService
from foxforge.domain.printers import PrinterEventKind, utc_now
from foxforge.domain.printers.capabilities import ThermalTelemetryCapability


def _encoded(target: int, current: int) -> int:
    return target * 65536 + current


def test_dual_nozzle_bed_and_chamber_are_normalized_without_wire_fields() -> None:
    codec = BambuThermalCodec()

    zones = codec.apply(
        {
            "print": {
                "command": "push_status",
                "device": {
                    "extruder": {
                        "info": [
                            {"id": 0, "temp": _encoded(250, 42)},
                            {"id": 1, "temp": _encoded(220, 39)},
                        ]
                    },
                    "bed": {"info": {"temp": _encoded(70, 60)}},
                    "ctc": {"info": {"temp": _encoded(45, 35), "target": 45}},
                },
            }
        }
    )

    by_id = {zone.zone_id: zone for zone in zones}
    assert by_id["hotend:right"].current_celsius == 42.0
    assert by_id["hotend:right"].target_celsius == 250.0
    assert by_id["hotend:left"].current_celsius == 39.0
    assert by_id["hotend:left"].target_celsius == 220.0
    assert by_id["bed"].current_celsius == 60.0
    assert by_id["bed"].target_celsius == 70.0
    assert by_id["chamber"].current_celsius == 35.0
    assert by_id["chamber"].target_celsius == 45.0


def test_sparse_temperature_update_preserves_unrelated_zones() -> None:
    codec = BambuThermalCodec()
    codec.apply(
        {
            "print": {
                "command": "push_status",
                "nozzle_temper": 32.0,
                "nozzle_target_temper": 0.0,
                "bed_temper": 30.0,
                "chamber_temper": 28.0,
            }
        }
    )

    zones = codec.apply({"print": {"command": "push_status", "bed_temper": 55.0}})
    by_id = {zone.zone_id: zone for zone in zones}

    assert by_id["hotend:0"].current_celsius == 32.0
    assert by_id["bed"].current_celsius == 55.0
    assert by_id["chamber"].current_celsius == 28.0


def test_malformed_sparse_values_preserve_last_valid_thermal_state() -> None:
    codec = BambuThermalCodec()
    codec.apply(
        {
            "print": {
                "command": "push_status",
                "nozzle_temper": 215.0,
                "nozzle_target_temper": 220.0,
                "bed_temper": 65.0,
                "bed_target_temper": 70.0,
                "chamber_temper": 35.0,
            }
        }
    )

    zones = codec.apply(
        {
            "print": {
                "command": "push_status",
                "nozzle_temper": "not-a-temperature",
                "nozzle_target_temper": 9999,
                "bed_temper": None,
                "bed_target_temper": -1,
                "chamber_temper": float("inf"),
            }
        }
    )
    by_id = {zone.zone_id: zone for zone in zones}

    assert (by_id["hotend:0"].current_celsius, by_id["hotend:0"].target_celsius) == (215.0, 220.0)
    assert (by_id["bed"].current_celsius, by_id["bed"].target_celsius) == (65.0, 70.0)
    assert by_id["chamber"].current_celsius == 35.0


def test_empty_dual_extruder_info_does_not_fabricate_thermal_zones() -> None:
    codec = BambuThermalCodec()

    zones = codec.apply(
        {
            "print": {
                "command": "push_status",
                "device": {"extruder": {"info": [{}, {}]}},
            }
        }
    )

    assert zones == ()


def test_temperature_only_native_change_emits_common_thermal_event(
    bambu_identity,
    bambu_idle_state,
    fake_bambu_transport,
) -> None:
    async def scenario() -> None:
        adapter = BambuAdapter(bambu_identity, fake_bambu_transport)
        await adapter.connect()
        events = adapter.events()
        try:
            updated = replace(
                bambu_idle_state,
                connected=True,
                observed_at=utc_now(),
                thermal_zones=(
                    BambuNativeThermalZone(
                        zone_id="hotend:right",
                        position=0,
                        current_celsius=41.0,
                        target_celsius=0.0,
                    ),
                ),
            )
            await fake_bambu_transport.push(updated)
            event = await asyncio.wait_for(anext(events), timeout=0.2)
            assert event.kind == PrinterEventKind.THERMAL_TELEMETRY_CHANGED
            assert event.payload.zones[0].zone_id == "hotend:0"
            assert event.payload.zones[0].kind.value == "hotend"
            assert event.payload.zones[0].current_celsius == 41.0
        finally:
            await events.aclose()  # type: ignore[attr-defined]
            await adapter.disconnect()

    asyncio.run(scenario())


def test_fleet_read_model_exposes_common_thermal_capability_without_bambu_wire_names(
    bambu_identity,
    bambu_idle_state,
    fake_bambu_transport,
) -> None:
    async def scenario() -> None:
        adapter = BambuAdapter(bambu_identity, fake_bambu_transport)
        await adapter.connect()
        events = adapter.events()
        try:
            updated = replace(
                bambu_idle_state,
                connected=True,
                observed_at=utc_now(),
                thermal_zones=(
                    BambuNativeThermalZone(
                        zone_id="hotend:right",
                        position=0,
                        current_celsius=215.0,
                        target_celsius=220.0,
                    ),
                    BambuNativeThermalZone(
                        zone_id="bed",
                        position=10,
                        current_celsius=68.0,
                        target_celsius=70.0,
                    ),
                ),
            )
            await fake_bambu_transport.push(updated)
            event = await asyncio.wait_for(anext(events), timeout=0.2)
            assert event.kind == PrinterEventKind.THERMAL_TELEMETRY_CHANGED

            capability = adapter.capability(ThermalTelemetryCapability)
            assert capability is not None
            payload = fleet_read_model(FleetService([adapter]))["printers"][0]
            descriptor = next(
                item for item in payload["capabilities"] if item["capabilityId"] == "foxforge.thermal_telemetry"
            )
            assert descriptor == {
                "capabilityId": "foxforge.thermal_telemetry",
                "majorVersion": 1,
                "reportsTargets": True,
            }
            assert payload["thermalTelemetry"]["zones"] == [
                {
                    "zoneId": "hotend:0",
                    "kind": "hotend",
                    "position": 0,
                    "label": "Right hotend",
                    "currentCelsius": 215.0,
                    "targetCelsius": 220.0,
                },
                {
                    "zoneId": "bed:0",
                    "kind": "bed",
                    "position": 10,
                    "label": "Bed",
                    "currentCelsius": 68.0,
                    "targetCelsius": 70.0,
                },
            ]
            serialized = repr(payload)
            for wire_name in ("nozzle_temper", "chamber_temper", "device.extruder.info", "bambu:thermal"):
                assert wire_name not in serialized
        finally:
            await events.aclose()  # type: ignore[attr-defined]
            await adapter.disconnect()

    asyncio.run(scenario())
