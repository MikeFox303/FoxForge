# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Private classification helpers for Bambu LAN print reports.

The transport initial-state gate and the incremental codec must share one
status-field vocabulary so newly observed firmware fields cannot be added to
one boundary while being forgotten at the other.
"""

from __future__ import annotations

from collections.abc import Mapping

_STATUS_META_FIELDS = frozenset({"command", "sequence_id"})
STATUS_FIELDS = frozenset(
    {
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
    }
)


def contains_status_fields(print_data: Mapping[str, object]) -> bool:
    """Return whether a print section contains a recognized state-bearing field."""

    return any(field in print_data for field in STATUS_FIELDS)


def is_initial_status_report(payload: Mapping[str, object]) -> bool:
    """Return whether a payload is sufficient to satisfy LAN initial-state preflight.

    A normal ``push_status`` is incremental, so any non-metadata field proves a
    real printer status report even when ``gcode_state`` is absent. A
    metadata-only frame is not enough. Legacy command-less reports must carry
    one of the recognized state fields. Command responses never satisfy the
    gate merely because they contain incidental data.
    """

    print_data = payload.get("print")
    if not isinstance(print_data, Mapping):
        return False

    command = print_data.get("command")
    if command == "push_status":
        return any(key not in _STATUS_META_FIELDS for key in print_data)

    if command is not None:
        return False
    return contains_status_fields(print_data)
