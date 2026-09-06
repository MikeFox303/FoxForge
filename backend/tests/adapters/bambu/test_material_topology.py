# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from foxforge.adapters.bambu.lan_codec import BambuLanCodec
from foxforge.adapters.bambu.material_topology import map_bambu_material_topology
from foxforge.adapters.bambu.native import (
    BambuMaterialUnitKind,
    BambuNativeMaterialUnit,
    BambuNativeState,
    BambuNativeTray,
)
from foxforge.domain.printers import utc_now
from foxforge.domain.printers.capabilities import MaterialRouteKind


def _state(*units: BambuNativeMaterialUnit, connected: bool = True) -> BambuNativeState:
    return BambuNativeState(
        connected=connected,
        gcode_state="IDLE",
        current_print=None,
        vendor_job_id=None,
        progress_percent=None,
        remaining_minutes=None,
        layer_num=None,
        total_layers=None,
        faults=(),
        material_units=units,
        observed_at=utc_now(),
    )


def _external(ams_id: int, material: str | None = None) -> BambuNativeMaterialUnit:
    return BambuNativeMaterialUnit(
        ams_id=ams_id,
        kind=BambuMaterialUnitKind.EXTERNAL,
        label="external",
        trays=(BambuNativeTray(ams_id=ams_id, tray_id=0, material_type=material),),
    )


def test_x2d_dual_external_pair_maps_to_left_and_right_toolheads() -> None:
    topology = map_bambu_material_topology("x2d", _state(_external(254), _external(255, "PLA")))

    assert [(toolhead.toolhead_id, toolhead.label) for toolhead in topology.toolheads] == [
        ("bambu:toolhead:0", "Right toolhead"),
        ("bambu:toolhead:1", "Left toolhead"),
    ]
    routes = {route.source_slot_id: route for route in topology.routes}
    assert routes["bambu:unit:254:tray:0"].kind == MaterialRouteKind.FIXED
    assert routes["bambu:unit:254:tray:0"].toolhead_ids == ("bambu:toolhead:1",)
    assert routes["bambu:unit:255:tray:0"].kind == MaterialRouteKind.FIXED
    assert routes["bambu:unit:255:tray:0"].toolhead_ids == ("bambu:toolhead:0",)


def test_single_external_254_does_not_claim_a_left_toolhead() -> None:
    topology = map_bambu_material_topology("single", _state(_external(254, "PLA")))

    assert topology.toolheads == ()
    assert len(topology.routes) == 1
    assert topology.routes[0].kind == MaterialRouteKind.UNKNOWN
    assert topology.routes[0].toolhead_ids == ()


def test_authoritative_ams_extruder_mapping_applies_to_every_slot() -> None:
    ams = BambuNativeMaterialUnit(
        ams_id=0,
        kind=BambuMaterialUnitKind.AMS_2_PRO,
        label="AMS 2 Pro 1",
        trays=(
            BambuNativeTray(ams_id=0, tray_id=0, material_type="PETG"),
            BambuNativeTray(ams_id=0, tray_id=1, material_type="PETG"),
        ),
        routed_extruder_id=1,
    )

    topology = map_bambu_material_topology("x2d", _state(ams))

    assert topology.toolheads[0].toolhead_id == "bambu:toolhead:1"
    assert all(route.kind == MaterialRouteKind.FIXED for route in topology.routes)
    assert all(route.toolhead_ids == ("bambu:toolhead:1",) for route in topology.routes)


def test_unknown_ams_routing_is_not_defaulted_to_right_toolhead() -> None:
    ams = BambuNativeMaterialUnit(
        ams_id=0,
        kind=BambuMaterialUnitKind.AMS_2_PRO,
        label="AMS 2 Pro 1",
        trays=(BambuNativeTray(ams_id=0, tray_id=0, material_type="PETG"),),
    )

    topology = map_bambu_material_topology("x2d", _state(ams))

    assert topology.toolheads == ()
    assert topology.routes[0].kind == MaterialRouteKind.UNKNOWN
    assert topology.routes[0].toolhead_ids == ()


def test_ams_info_bits_are_retained_and_0xe_fails_closed() -> None:
    codec = BambuLanCodec()

    right = codec.apply(
        {
            "print": {
                "command": "push_status",
                "ams": {"ams": [{"id": 0, "info": "10001003", "tray": [{"id": 0, "tray_type": "PETG"}]}]},
            }
        }
    )
    assert right is not None
    assert right.material_units[0].routed_extruder_id == 0

    left = codec.apply(
        {
            "print": {
                "command": "push_status",
                "ams": {"ams": [{"id": 0, "info": "10002104", "tray": [{"id": 0, "tray_type": "PETG"}]}]},
            }
        }
    )
    assert left is not None
    assert left.material_units[0].routed_extruder_id == 1

    dynamic_or_unknown = codec.apply(
        {
            "print": {
                "command": "push_status",
                "ams": {"ams": [{"id": 0, "info": "00000E00", "tray": [{"id": 0, "tray_type": "PETG"}]}]},
            }
        }
    )
    assert dynamic_or_unknown is not None
    assert dynamic_or_unknown.material_units[0].routed_extruder_id is None


def test_partial_ams_update_without_info_preserves_previous_route() -> None:
    codec = BambuLanCodec()
    initial = codec.apply(
        {
            "print": {
                "command": "push_status",
                "ams": {"ams": [{"id": 0, "info": "10002104", "tray": [{"id": 0, "tray_type": "PETG"}]}]},
            }
        }
    )
    assert initial is not None
    assert initial.material_units[0].routed_extruder_id == 1

    partial = codec.apply(
        {
            "print": {
                "command": "push_status",
                "ams": {"ams": [{"id": 0, "tray": [{"id": 0, "tray_type": "PETG", "remain": 75}]}]},
            }
        }
    )

    assert partial is not None
    assert partial.material_units[0].routed_extruder_id == 1


def test_topology_stale_tracks_transport_connection() -> None:
    topology = map_bambu_material_topology("x2d", _state(_external(254), _external(255), connected=False))

    assert topology.stale is True
