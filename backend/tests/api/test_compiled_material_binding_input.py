# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

import pytest

from foxforge.api.v1.queue_commands import _material_bindings


def test_queue_input_cannot_supply_compiled_toolhead_identity() -> None:
    with pytest.raises(ValueError, match="unknown field"):
        _material_bindings(
            [
                {
                    "materialIndex": 0,
                    "slotId": "bambu:unit:0:tray:0",
                    "toolheadId": "bambu:toolhead:0",
                }
            ]
        )
