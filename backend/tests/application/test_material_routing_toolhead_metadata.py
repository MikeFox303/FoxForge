# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime

from foxforge.application.artifacts import (
    ArtifactPrintPlan,
    PrintPlanIssue,
    PrintPlanIssueCode,
    PrintPlanIssueSeverity,
    PrintPlanMaterialRequirement,
    PrintPlanPlate,
    inspect_print_plan,
)
from foxforge.application.routing import MaterialRoutingBlockerCode, compile_material_routing
from foxforge.domain.printers.capabilities import (
    DetectedMaterial,
    LocalPrintArtifact,
    MaterialActivity,
    MaterialBinding,
    MaterialPresence,
    MaterialRouteKind,
    MaterialRouteSnapshot,
    MaterialSlotSnapshot,
    MaterialSystemSnapshot,
    MaterialToolheadSnapshot,
    MaterialTopologySnapshot,
    MaterialUnitKind,
    MaterialUnitSnapshot,
    PrintArtifactFormat,
)


def _routing_evidence() -> tuple[MaterialSystemSnapshot, MaterialTopologySnapshot]:
    detected = DetectedMaterial(
        material_family="PETG",
        vendor_name=None,
        product_name=None,
        color=None,
        tag=None,
        remaining_fraction=None,
    )
    slot = MaterialSlotSnapshot(
        slot_id="source:0",
        unit_id="unit:0",
        position=0,
        label=None,
        presence=MaterialPresence.LOADED,
        activity=MaterialActivity.UNKNOWN,
        detected_material=detected,
    )
    observed_at = datetime(2026, 9, 6, tzinfo=UTC)
    material_system = MaterialSystemSnapshot(
        printer_id="printer-1",
        units=(MaterialUnitSnapshot("unit:0", MaterialUnitKind.EXTERNAL, None, 0, (slot,)),),
        observed_at=observed_at,
        stale=False,
    )
    topology = MaterialTopologySnapshot(
        printer_id="printer-1",
        toolheads=(MaterialToolheadSnapshot("toolhead:0", "Right", 0),),
        routes=(MaterialRouteSnapshot("source:0", ("toolhead:0",), MaterialRouteKind.FIXED),),
        observed_at=observed_at,
        stale=False,
    )
    return material_system, topology


def _artifact_with_invalid_physical_map(tmp_path) -> LocalPrintArtifact:
    path = (tmp_path / "invalid-toolhead-map.3mf").resolve()
    settings = json.dumps(
        {
            "filament_type": ["PETG"],
            "filament_nozzle_map": ["0"],
            "physical_extruder_map": ["invalid", "0"],
        }
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/project_settings.config", settings)
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


def test_invalid_plate_toolhead_metadata_blocks_even_a_fixed_source_route() -> None:
    plan = ArtifactPrintPlan(
        artifact_id="a" * 64,
        artifact_sha256="a" * 64,
        plates=(
            PrintPlanPlate(
                plate_index=0,
                material_requirements=(
                    PrintPlanMaterialRequirement(
                        material_index=0,
                        material_family="PETG",
                        color_rgba_hex=None,
                        profile_name=None,
                        expected_toolhead_position=None,
                    ),
                ),
                ready_for_routing=True,
            ),
        ),
        issues=(
            PrintPlanIssue(
                code=PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID,
                severity=PrintPlanIssueSeverity.WARNING,
                message="slice_info.config contains partial toolhead assignments",
                plate_index=0,
            ),
        ),
    )
    material_system, topology = _routing_evidence()

    result = compile_material_routing(
        plan=plan,
        selection=None,
        bindings=(MaterialBinding(0, "source:0"),),
        material_system=material_system,
        topology=topology,
    )

    assert result.eligible is False
    assert result.bindings == ()
    assert [blocker.code for blocker in result.blockers] == [MaterialRoutingBlockerCode.PRINT_PLAN_BLOCKED]


def test_invalid_physical_map_cannot_be_masked_by_a_fixed_source_route(tmp_path) -> None:
    plan = inspect_print_plan(_artifact_with_invalid_physical_map(tmp_path))
    material_system, topology = _routing_evidence()

    assert any(issue.code == PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID for issue in plan.issues)
    assert plan.plates[0].material_requirements[0].expected_toolhead_position is None

    result = compile_material_routing(
        plan=plan,
        selection=None,
        bindings=(MaterialBinding(0, "source:0"),),
        material_system=material_system,
        topology=topology,
    )

    assert result.eligible is False
    assert result.bindings == ()
    assert [blocker.code for blocker in result.blockers] == [MaterialRoutingBlockerCode.PRINT_PLAN_BLOCKED]
