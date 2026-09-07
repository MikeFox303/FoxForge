# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import pytest

from foxforge.adapters.bambu.lan_reports import contains_status_fields, is_initial_status_report


@pytest.mark.parametrize(
    "field",
    [
        "gcode_state",
        "subtask_name",
        "gcode_file",
        "mc_percent",
        "mc_remaining_time",
        "layer_num",
        "total_layer_num",
        "ams",
        "vt_tray",
        "vir_slot",
        "device",
        "wifi_signal",
        "print_error",
        "hms",
    ],
)
def test_status_field_vocabulary_is_shared_for_known_state_fields(field: str) -> None:
    assert contains_status_fields({field: object()}) is True


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"print": {"command": "push_status", "sequence_id": "1"}}, False),
        ({"print": {"command": "push_status", "device": {}}}, True),
        ({"print": {"command": "push_status", "wifi_signal": "-63dBm"}}, True),
        ({"print": {"command": "push_status", "vir_slot": []}}, True),
        ({"print": {"device": {}}}, True),
        ({"print": {"vir_slot": []}}, True),
        ({"print": {"command": "project_file", "device": {}}}, False),
        ({"print": {"command": "pause", "gcode_state": "PAUSE"}}, False),
        ({"info": {"command": "get_version", "module": []}}, False),
        ({"print": "not-a-mapping"}, False),
        ({}, False),
    ],
)
def test_initial_status_report_matrix(payload: dict[str, object], expected: bool) -> None:
    assert is_initial_status_report(payload) is expected


def test_unknown_push_status_extension_is_still_state_bearing() -> None:
    payload = {
        "print": {
            "command": "push_status",
            "sequence_id": "2",
            "future_firmware_field": {"value": 1},
        }
    }

    assert is_initial_status_report(payload) is True
    assert contains_status_fields(payload["print"]) is False  # type: ignore[arg-type]
