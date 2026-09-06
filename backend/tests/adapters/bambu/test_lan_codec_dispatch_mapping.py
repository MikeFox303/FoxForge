# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from pathlib import Path

import pytest

from foxforge.adapters.bambu.lan_codec import build_project_file_command
from foxforge.adapters.bambu.native import BambuNativeMaterialRoute, BambuNativePrintRequest


def _request(*routes: BambuNativeMaterialRoute) -> BambuNativePrintRequest:
    return BambuNativePrintRequest(
        local_path=Path("/tmp/foxforge.3mf"),
        filename="foxforge.3mf",
        plate_number=1,
        material_routes=routes,
        requested_name="FoxForge mapping test",
    )


def _print_command(*routes: BambuNativeMaterialRoute) -> dict[str, object]:
    payload = build_project_file_command(
        "42",
        _request(*routes),
        "foxforge.3mf",
        "ftp:///foxforge.3mf",
    )
    command = payload["print"]
    assert isinstance(command, dict)
    return command


def test_regular_ams_mapping_remains_unchanged() -> None:
    command = _print_command(
        BambuNativeMaterialRoute(material_index=0, ams_id=0, tray_id=1),
        BambuNativeMaterialRoute(material_index=1, ams_id=0, tray_id=3),
    )

    assert command["use_ams"] is True
    assert command["ams_mapping"] == [1, 3]
    assert command["ams_mapping2"] == [
        {"ams_id": 0, "slot_id": 1},
        {"ams_id": 0, "slot_id": 3},
    ]
    assert "nozzle_mapping" not in command


def test_external_left_uses_minus_one_flat_and_real_id_in_mapping2() -> None:
    command = _print_command(BambuNativeMaterialRoute(material_index=0, ams_id=254, tray_id=0))

    assert command["use_ams"] is True
    assert command["ams_mapping"] == [-1]
    assert command["ams_mapping2"] == [{"ams_id": 254, "slot_id": 0}]


def test_external_right_uses_minus_one_flat_and_real_id_in_mapping2() -> None:
    command = _print_command(BambuNativeMaterialRoute(material_index=0, ams_id=255, tray_id=0))

    assert command["use_ams"] is True
    assert command["ams_mapping"] == [-1]
    assert command["ams_mapping2"] == [{"ams_id": 255, "slot_id": 0}]


def test_mixed_ams_and_external_routes_keep_material_index_order() -> None:
    command = _print_command(
        BambuNativeMaterialRoute(material_index=2, ams_id=255, tray_id=0),
        BambuNativeMaterialRoute(material_index=0, ams_id=0, tray_id=2),
        BambuNativeMaterialRoute(material_index=1, ams_id=254, tray_id=0),
    )

    assert command["use_ams"] is True
    assert command["ams_mapping"] == [2, -1, -1]
    assert command["ams_mapping2"] == [
        {"ams_id": 0, "slot_id": 2},
        {"ams_id": 254, "slot_id": 0},
        {"ams_id": 255, "slot_id": 0},
    ]


def test_compiled_nozzle_mapping_is_aligned_by_material_index() -> None:
    command = _print_command(
        BambuNativeMaterialRoute(material_index=2, ams_id=0, tray_id=2, nozzle_index=0),
        BambuNativeMaterialRoute(material_index=0, ams_id=0, tray_id=0, nozzle_index=1),
    )

    assert command["ams_mapping"] == [0, -1, 2]
    assert command["nozzle_mapping"] == [1, -1, 0]


def test_dual_external_nozzle_mapping_uses_compiled_toolhead_indices() -> None:
    command = _print_command(
        BambuNativeMaterialRoute(material_index=1, ams_id=255, tray_id=0, nozzle_index=0),
        BambuNativeMaterialRoute(material_index=0, ams_id=254, tray_id=0, nozzle_index=1),
    )

    assert command["ams_mapping"] == [-1, -1]
    assert command["ams_mapping2"] == [
        {"ams_id": 254, "slot_id": 0},
        {"ams_id": 255, "slot_id": 0},
    ]
    assert command["nozzle_mapping"] == [1, 0]


def test_native_print_request_rejects_partial_nozzle_mapping() -> None:
    with pytest.raises(ValueError, match="partial nozzle mapping"):
        _request(
            BambuNativeMaterialRoute(material_index=0, ams_id=0, tray_id=0, nozzle_index=0),
            BambuNativeMaterialRoute(material_index=1, ams_id=0, tray_id=1),
        )
