# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
import json
import zipfile

import pytest

from foxforge.application.artifacts import (
    ArtifactChangedDuringInspectionError,
    InvalidThreeMfError,
    PrintPlanIssueCode,
    PrintPlanIssueSeverity,
    inspect_print_plan,
)
from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat


def _artifact(tmp_path, files: list[tuple[str, bytes | str]]) -> LocalPrintArtifact:
    path = (tmp_path / "job.3mf").resolve()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files:
            archive.writestr(name, content)
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


def _project_settings(*, families: list[str], colors: list[str], profiles: list[str]) -> str:
    return json.dumps(
        {
            "filament_type": families,
            "filament_colour": colors,
            "filament_settings_id": profiles,
        }
    )


def test_single_plate_uses_executable_m620_material_indices(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _project_settings(
                    families=["PLA", "PETG"],
                    colors=["#112233", "AABBCCDD"],
                    profiles=["PLA profile", "PETG profile"],
                ),
            ),
            (
                "Metadata/plate_1.gcode",
                "M620 S0A\nG1 X1 Y1\nM620 S1A\nM620 S255\n",
            ),
        ],
    )

    plan = inspect_print_plan(artifact)

    assert plan.ready_for_routing is True
    assert plan.issues == ()
    assert len(plan.plates) == 1
    plate = plan.plates[0]
    assert plate.plate_index == 0
    assert plate.ready_for_routing is True
    assert [item.material_index for item in plate.material_requirements] == [0, 1]
    assert plate.material_requirements[0].material_family == "PLA"
    assert plate.material_requirements[0].color_rgba_hex == "112233FF"
    assert plate.material_requirements[0].profile_name == "PLA profile"
    assert plate.material_requirements[1].material_family == "PETG"
    assert plate.material_requirements[1].color_rgba_hex == "AABBCCDD"


def test_multi_plate_material_requirements_are_plate_scoped(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _project_settings(
                    families=["PLA", "PETG", "ABS"],
                    colors=["#111111", "#222222", "#333333"],
                    profiles=["p0", "p1", "p2"],
                ),
            ),
            ("Metadata/plate_2.gcode", "M620 S2A\nG1 E1\n"),
            ("Metadata/plate_1.gcode", "M620 S0A\nM620 S1A\nG1 E1\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    assert [plate.plate_index for plate in plan.plates] == [0, 1]
    assert [item.material_index for item in plan.plates[0].material_requirements] == [0, 1]
    assert [item.material_index for item in plan.plates[1].material_requirements] == [2]
    assert all(plate.ready_for_routing for plate in plan.plates)


def test_missing_project_metadata_does_not_invent_material_identity(tmp_path) -> None:
    artifact = _artifact(tmp_path, [("Metadata/plate_1.gcode", "M620 S0A\n")])

    plan = inspect_print_plan(artifact)

    assert plan.ready_for_routing is True
    requirement = plan.plates[0].material_requirements[0]
    assert requirement.material_index == 0
    assert requirement.material_family is None
    assert requirement.color_rgba_hex is None
    assert requirement.profile_name is None


def test_invalid_project_metadata_warns_for_description_and_toolhead_routing(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            ("Metadata/project_settings.config", "{not-json"),
            ("Metadata/plate_1.gcode", "M620 S3A\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    assert plan.ready_for_routing is True
    assert [(issue.code, issue.severity, issue.plate_index) for issue in plan.issues] == [
        (PrintPlanIssueCode.PROJECT_METADATA_INVALID, PrintPlanIssueSeverity.WARNING, None),
        (PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID, PrintPlanIssueSeverity.WARNING, 0),
    ]
    assert plan.plates[0].material_requirements[0].material_index == 3


def test_plate_without_numeric_m620_fails_closed(tmp_path) -> None:
    artifact = _artifact(tmp_path, [("Metadata/plate_1.gcode", "G28\nG1 X1 Y1\n")])

    plan = inspect_print_plan(artifact)

    assert plan.ready_for_routing is False
    assert plan.plates[0].ready_for_routing is False
    assert plan.plates[0].material_requirements == ()
    issue = plan.issues[0]
    assert issue.code == PrintPlanIssueCode.MATERIAL_REQUIREMENTS_UNKNOWN
    assert issue.severity == PrintPlanIssueSeverity.BLOCKING
    assert issue.plate_index == 0


def test_out_of_range_material_index_blocks_plate_even_with_valid_requirement(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [("Metadata/plate_1.gcode", "M620 S0A\nM620 S999A\n")],
    )

    plan = inspect_print_plan(artifact)

    assert plan.ready_for_routing is False
    assert plan.plates[0].ready_for_routing is False
    assert [item.material_index for item in plan.plates[0].material_requirements] == [0]
    assert any(issue.code == PrintPlanIssueCode.MATERIAL_INDEX_OUT_OF_RANGE for issue in plan.issues)


def test_unsliced_3mf_has_explicit_blocking_issue(tmp_path) -> None:
    artifact = _artifact(tmp_path, [("3D/3dmodel.model", "<model/>")])

    plan = inspect_print_plan(artifact)

    assert plan.ready_for_routing is False
    assert plan.plates == ()
    assert plan.issues[0].code == PrintPlanIssueCode.NO_SLICED_PLATES
    assert plan.issues[0].severity == PrintPlanIssueSeverity.BLOCKING


def test_duplicate_plate_gcode_members_are_rejected_as_ambiguous(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            ("Metadata/plate_1.gcode", "M620 S0A\n"),
            ("metadata/PLATE_1.GCODE", "M620 S1A\n"),
        ],
    )

    with pytest.raises(InvalidThreeMfError, match="more than one G-code member"):
        inspect_print_plan(artifact)


def test_invalid_zip_is_rejected(tmp_path) -> None:
    path = (tmp_path / "invalid.3mf").resolve()
    payload = b"not-a-zip"
    path.write_bytes(payload)
    artifact = LocalPrintArtifact(
        artifact_id=hashlib.sha256(payload).hexdigest(),
        path=path,
        filename=path.name,
        format=PrintArtifactFormat.THREE_MF,
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )

    with pytest.raises(InvalidThreeMfError):
        inspect_print_plan(artifact)


def test_changed_staged_artifact_is_rejected_before_parsing(tmp_path) -> None:
    artifact = _artifact(tmp_path, [("Metadata/plate_1.gcode", "M620 S0A\n")])
    artifact.path.write_bytes(b"changed-after-staging")

    with pytest.raises(ArtifactChangedDuringInspectionError, match="size no longer matches"):
        inspect_print_plan(artifact)
