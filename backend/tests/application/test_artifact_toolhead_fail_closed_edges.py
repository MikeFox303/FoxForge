# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
import json
import zipfile

from foxforge.application.artifacts import PrintPlanIssueCode, inspect_print_plan
from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat


def _artifact(tmp_path, settings: dict[str, object], slice_info: str) -> LocalPrintArtifact:
    path = (tmp_path / "toolhead-edge.3mf").resolve()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/project_settings.config", json.dumps(settings))
        archive.writestr("Metadata/slice_info.config", slice_info)
        archive.writestr("Metadata/plate_1.gcode", "M620 S0A\n")
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    return LocalPrintArtifact(
        artifact_id=digest,
        path=path,
        filename=path.name,
        format=PrintArtifactFormat.THREE_MF,
        size_bytes=len(payload),
        sha256=digest,
    )


def _toolhead_warnings(plan) -> list:
    return [issue for issue in plan.issues if issue.code == PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID]


def test_explicit_group_without_physical_map_is_invalid_not_absent(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        {"filament_type": ["PETG"]},
        '<config><plate><metadata key="index" value="1"/><filament id="1" group_id="0"/></plate></config>',
    )

    plan = inspect_print_plan(artifact)

    assert plan.plates[0].material_requirements[0].expected_toolhead_position is None
    warnings = _toolhead_warnings(plan)
    assert len(warnings) == 1
    assert warnings[0].plate_index == 0
    assert "physical_extruder_map" in warnings[0].message


def test_single_toolhead_project_rejects_out_of_range_explicit_group(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        {
            "filament_type": ["PETG"],
            "physical_extruder_map": ["0"],
            "filament_nozzle_map": ["0"],
        },
        '<config><plate><metadata key="index" value="1"/><filament id="1" group_id="1"/></plate></config>',
    )

    plan = inspect_print_plan(artifact)

    assert plan.plates[0].material_requirements[0].expected_toolhead_position is None
    warnings = _toolhead_warnings(plan)
    assert len(warnings) == 1
    assert "single-toolhead" in warnings[0].message


def test_single_toolhead_project_accepts_consistent_group_without_claiming_dual_route(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        {
            "filament_type": ["PETG"],
            "physical_extruder_map": ["0"],
            "filament_nozzle_map": ["0"],
        },
        '<config><plate><metadata key="index" value="1"/><filament id="1" group_id="0"/></plate></config>',
    )

    plan = inspect_print_plan(artifact)

    assert plan.plates[0].material_requirements[0].expected_toolhead_position is None
    assert _toolhead_warnings(plan) == []
