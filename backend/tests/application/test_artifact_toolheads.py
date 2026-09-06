# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
import json
import zipfile

from foxforge.application.artifacts import PrintPlanIssueCode, inspect_print_plan
from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat


def _artifact(tmp_path, files: list[tuple[str, bytes | str]]) -> LocalPrintArtifact:
    path = (tmp_path / "toolheads.3mf").resolve()
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


def _settings(*, nozzle_map: list[str], physical_map: list[str]) -> str:
    return json.dumps(
        {
            "filament_type": ["PETG", "PLA"],
            "filament_nozzle_map": nozzle_map,
            "physical_extruder_map": physical_map,
        }
    )


def test_slice_group_assignment_overrides_project_nozzle_preference(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _settings(nozzle_map=["0"], physical_map=["1", "0"]),
            ),
            (
                "Metadata/slice_info.config",
                '<config><plate><metadata key="index" value="1"/><filament id="1" group_id="1"/></plate></config>',
            ),
            ("Metadata/plate_1.gcode", "M620 S0A\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    requirement = plan.plates[0].material_requirements[0]
    assert requirement.material_index == 0
    assert requirement.expected_toolhead_position == 0
    assert not any(issue.code == PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID for issue in plan.issues)


def test_toolhead_expectations_are_plate_scoped(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _settings(nozzle_map=["0"], physical_map=["1", "0"]),
            ),
            (
                "Metadata/slice_info.config",
                "<config>"
                '<plate><metadata key="index" value="1"/><filament id="1" group_id="0"/></plate>'
                '<plate><metadata key="index" value="2"/><filament id="1" group_id="1"/></plate>'
                "</config>",
            ),
            ("Metadata/plate_1.gcode", "M620 S0A\n"),
            ("Metadata/plate_2.gcode", "M620 S0A\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    assert plan.plates[0].material_requirements[0].expected_toolhead_position == 1
    assert plan.plates[1].material_requirements[0].expected_toolhead_position == 0


def test_nozzle_group_table_maps_group_to_slicer_extruder_before_physical_map(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _settings(nozzle_map=["0"], physical_map=["1", "0"]),
            ),
            (
                "Metadata/slice_info.config",
                '<config><plate><metadata key="index" value="1"/>'
                '<nozzle id="7" extruder_id="2"/>'
                '<filament id="1" group_id="7"/></plate></config>',
            ),
            ("Metadata/plate_1.gcode", "M620 S0A\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    assert plan.plates[0].material_requirements[0].expected_toolhead_position == 0


def test_project_nozzle_map_is_fallback_when_slice_has_no_group_assignments(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _settings(nozzle_map=["1", "0"], physical_map=["1", "0"]),
            ),
            (
                "Metadata/slice_info.config",
                '<config><plate><metadata key="index" value="1"/><filament id="1"/></plate></config>',
            ),
            ("Metadata/plate_1.gcode", "M620 S0A\nM620 S1A\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    requirements = {item.material_index: item for item in plan.plates[0].material_requirements}
    assert requirements[0].expected_toolhead_position == 0
    assert requirements[1].expected_toolhead_position == 1


def test_partial_actual_group_metadata_suppresses_project_fallback(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _settings(nozzle_map=["0", "1"], physical_map=["1", "0"]),
            ),
            (
                "Metadata/slice_info.config",
                '<config><plate><metadata key="index" value="1"/>'
                '<filament id="1" group_id="0"/><filament id="2"/></plate></config>',
            ),
            ("Metadata/plate_1.gcode", "M620 S0A\nM620 S1A\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    assert all(item.expected_toolhead_position is None for item in plan.plates[0].material_requirements)
    warnings = [issue for issue in plan.issues if issue.code == PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID]
    assert len(warnings) == 1
    assert warnings[0].plate_index == 0


def test_forbidden_xml_declarations_fail_closed_without_using_fallback(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _settings(nozzle_map=["0"], physical_map=["1", "0"]),
            ),
            (
                "Metadata/slice_info.config",
                '<!DOCTYPE config [<!ENTITY x "boom">]><config><plate>'
                '<metadata key="index" value="1"/><filament id="1" group_id="0"/>'
                "</plate></config>",
            ),
            ("Metadata/plate_1.gcode", "M620 S0A\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    assert plan.plates[0].material_requirements[0].expected_toolhead_position is None
    warning = next(issue for issue in plan.issues if issue.code == PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID)
    assert "DTD/entity" in warning.message


def test_invalid_physical_extruder_map_is_not_treated_as_absent_toolhead_intent(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _settings(nozzle_map=["0"], physical_map=["invalid", "0"]),
            ),
            ("Metadata/plate_1.gcode", "M620 S0A\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    assert plan.plates[0].material_requirements[0].expected_toolhead_position is None
    warnings = [issue for issue in plan.issues if issue.code == PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID]
    assert len(warnings) == 1
    assert warnings[0].plate_index == 0
    assert "physical_extruder_map" in warnings[0].message


def test_invalid_fallback_only_blocks_plates_that_need_the_fallback(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _settings(nozzle_map=["invalid"], physical_map=["1", "0"]),
            ),
            (
                "Metadata/slice_info.config",
                "<config>"
                '<plate><metadata key="index" value="1"/><filament id="1" group_id="1"/></plate>'
                '<plate><metadata key="index" value="2"/><filament id="1"/></plate>'
                "</config>",
            ),
            ("Metadata/plate_1.gcode", "M620 S0A\n"),
            ("Metadata/plate_2.gcode", "M620 S0A\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    assert plan.plates[0].material_requirements[0].expected_toolhead_position == 0
    assert plan.plates[1].material_requirements[0].expected_toolhead_position is None
    warnings = [issue for issue in plan.issues if issue.code == PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID]
    assert [warning.plate_index for warning in warnings] == [1]
    assert "filament_nozzle_map" in warnings[0].message


def test_single_nozzle_project_does_not_claim_a_toolhead_expectation(tmp_path) -> None:
    artifact = _artifact(
        tmp_path,
        [
            (
                "Metadata/project_settings.config",
                _settings(nozzle_map=["0"], physical_map=["0"]),
            ),
            ("Metadata/plate_1.gcode", "M620 S0A\n"),
        ],
    )

    plan = inspect_print_plan(artifact)

    assert plan.plates[0].material_requirements[0].expected_toolhead_position is None
    assert not any(issue.code == PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID for issue in plan.issues)
