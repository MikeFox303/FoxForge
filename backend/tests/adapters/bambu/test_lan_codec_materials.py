# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from foxforge.adapters.bambu.lan_codec import BambuLanCodec
from foxforge.adapters.bambu.mapping import map_bambu_material_system
from foxforge.adapters.bambu.native import BambuMaterialUnitKind
from foxforge.domain.printers.capabilities import MaterialPresence, MaterialUnitKind


def _x2d_status() -> dict[str, object]:
    return {
        "print": {
            "command": "push_status",
            "gcode_state": "IDLE",
            "ams": {
                "tray_now": "255",
                "tray_exist_bits": "F",
                "ams": [
                    {
                        "id": "0",
                        "tray": [
                            {"id": "0", "tray_type": "PETG", "tray_color": "FF6600FF", "remain": 91},
                            {"id": "1", "tray_type": "PETG", "tray_color": "FFFFFFFF", "remain": 83},
                            {"id": "2", "tray_type": "PETG", "tray_color": "00FF00FF", "remain": 72},
                            {"id": "3", "tray_type": "PETG", "tray_color": "0000FFFF", "remain": 64},
                        ],
                    }
                ],
            },
            "vt_tray": [
                {
                    "id": 254,
                    "state": 9,
                    "tray_type": "",
                    "tray_color": "",
                    "tray_sub_brands": "",
                    "remain": 0,
                },
                {
                    "id": 255,
                    "state": 0,
                    "tray_type": "PLA",
                    "tray_color": "FFFFFFFF",
                    "tray_sub_brands": "PLA Basic",
                    "remain": 48,
                },
            ],
        }
    }


def _mark_ams_2_pro(codec: BambuLanCodec) -> None:
    codec.apply(
        {
            "info": {
                "command": "get_version",
                "module": [{"name": "n3f/0"}],
            }
        }
    )


def test_x2d_dual_external_sources_and_ams_2_pro_are_preserved() -> None:
    codec = BambuLanCodec()
    _mark_ams_2_pro(codec)

    state = codec.apply(_x2d_status())

    assert state is not None
    assert [unit.ams_id for unit in state.material_units] == [0, 254, 255]

    ams, external_left, external_right = state.material_units
    assert ams.kind == BambuMaterialUnitKind.AMS_2_PRO
    assert ams.label == "AMS 2 Pro 1"
    assert [tray.material_type for tray in ams.trays] == ["PETG", "PETG", "PETG", "PETG"]

    assert external_left.kind == BambuMaterialUnitKind.EXTERNAL
    assert external_left.label == "External Left"
    assert external_left.trays[0].exists is False
    assert external_left.trays[0].material_type is None

    assert external_right.kind == BambuMaterialUnitKind.EXTERNAL
    assert external_right.label == "External Right"
    assert external_right.trays[0].exists is True
    assert external_right.trays[0].material_type == "PLA"
    assert external_right.trays[0].product_name == "PLA Basic"

    common = map_bambu_material_system("x2d", state)
    assert [unit.kind for unit in common.units] == [
        MaterialUnitKind.MULTI_SLOT,
        MaterialUnitKind.EXTERNAL,
        MaterialUnitKind.EXTERNAL,
    ]
    assert common.units[1].slots[0].presence == MaterialPresence.EMPTY
    assert common.units[2].slots[0].presence == MaterialPresence.LOADED
    assert common.units[2].slots[0].detected_material is not None
    assert common.units[2].slots[0].detected_material.material_family == "PLA"


def test_legacy_single_external_dict_keeps_254_compatibility() -> None:
    codec = BambuLanCodec()

    state = codec.apply(
        {
            "print": {
                "command": "push_status",
                "vt_tray": {
                    "tray_type": "TPU",
                    "tray_color": "111111FF",
                    "remain": 36,
                },
            }
        }
    )

    assert state is not None
    assert len(state.material_units) == 1
    external = state.material_units[0]
    assert external.ams_id == 254
    assert external.label == "External Left"
    assert external.trays[0].material_type == "TPU"
    assert external.trays[0].exists is True


def test_incremental_ams_and_external_updates_do_not_erase_each_other() -> None:
    codec = BambuLanCodec()
    _mark_ams_2_pro(codec)
    initial = codec.apply(_x2d_status())
    assert initial is not None
    assert [unit.ams_id for unit in initial.material_units] == [0, 254, 255]

    external_update = codec.apply(
        {
            "print": {
                "command": "push_status",
                "vt_tray": [
                    {"id": 254, "state": 9},
                    {
                        "id": 255,
                        "state": 0,
                        "tray_type": "PLA",
                        "tray_color": "FFFFFFFF",
                        "remain": 41,
                    },
                ],
            }
        }
    )
    assert external_update is not None
    assert [unit.ams_id for unit in external_update.material_units] == [0, 254, 255]
    assert external_update.material_units[0].kind == BambuMaterialUnitKind.AMS_2_PRO
    assert external_update.material_units[2].trays[0].remaining_percent == 41

    ams_update = codec.apply(
        {
            "print": {
                "command": "push_status",
                "ams": {
                    "tray_exist_bits": "F",
                    "ams": [
                        {
                            "id": 0,
                            "tray": [
                                {"id": 0, "tray_type": "PETG", "remain": 90},
                                {"id": 1, "tray_type": "PETG", "remain": 82},
                                {"id": 2, "tray_type": "PETG", "remain": 71},
                                {"id": 3, "tray_type": "PETG", "remain": 63},
                            ],
                        }
                    ],
                },
            }
        }
    )
    assert ams_update is not None
    assert [unit.ams_id for unit in ams_update.material_units] == [0, 254, 255]
    assert ams_update.material_units[0].trays[0].remaining_percent == 90
    assert ams_update.material_units[2].trays[0].material_type == "PLA"


def test_empty_vt_tray_list_clears_only_external_sources() -> None:
    codec = BambuLanCodec()
    _mark_ams_2_pro(codec)
    initial = codec.apply(_x2d_status())
    assert initial is not None

    updated = codec.apply({"print": {"command": "push_status", "vt_tray": []}})

    assert updated is not None
    assert [unit.ams_id for unit in updated.material_units] == [0]
    assert updated.material_units[0].kind == BambuMaterialUnitKind.AMS_2_PRO


def test_list_entry_without_physical_id_is_not_guessed() -> None:
    codec = BambuLanCodec()

    state = codec.apply(
        {
            "print": {
                "command": "push_status",
                "vt_tray": [{"tray_type": "PLA", "tray_color": "FFFFFFFF"}],
            }
        }
    )

    assert state is not None
    assert state.material_units == ()
