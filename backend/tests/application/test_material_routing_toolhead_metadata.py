# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from datetime import UTC, datetime

from foxforge.application.artifacts import (
    ArtifactPrintPlan,
    PrintPlanIssue,
    PrintPlanIssueCode,
    PrintPlanIssueSeverity,
    PrintPlanMaterialRequirement,
    PrintPlanPlate,
)
from foxforge.application.routing import MaterialRoutingBlockerCode, compile_material_routing
from foxforge.domain.printers.capabilities import (
    DetectedMaterial,
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
