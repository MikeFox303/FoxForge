# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

import pytest

from foxforge.domain.printers.capabilities import MaterialBinding


def test_material_binding_normalizes_compiled_toolhead_identity() -> None:
    binding = MaterialBinding(2, "bambu:unit:255:tray:0", "  bambu:toolhead:0  ")

    assert binding.material_index == 2
    assert binding.slot_id == "bambu:unit:255:tray:0"
    assert binding.toolhead_id == "bambu:toolhead:0"


def test_material_binding_rejects_blank_compiled_toolhead_identity() -> None:
    with pytest.raises(ValueError, match="toolhead_id"):
        MaterialBinding(0, "bambu:unit:0:tray:0", "   ")
