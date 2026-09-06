# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from datetime import UTC, datetime

from foxforge.application.artifacts import ArtifactPrintPlan, PrintPlanMaterialRequirement, PrintPlanPlate
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
    PrintArtifactSelection,
)

_NOW = datetime(2026, 9, 6, tzinfo=UTC)
_PRINTER_ID = "printer-1"
_SLOT_0 = "source:0"
_SLOT_1 = "source:1"
_TOOL_0 = "toolhead:0"
_TOOL_1 = "toolhead:1"


def _requirement(
    material_index: int,
    *,
    family: str | None = "PETG",
    toolhead_position: int | None = None,
) -> PrintPlanMaterialRequirement:
    return PrintPlanMaterialRequirement(
        material_index=material_index,
        material_family=family,
        color_rgba_hex="112233FF",
        profile_name="test profile",
        expected_toolhead_position=toolhead_position,
    )


def _plan(*plates: PrintPlanPlate) -> ArtifactPrintPlan:
    return ArtifactPrintPlan(
        artifact_id="a" * 64,
        artifact_sha256="a" * 64,
        plates=plates,
        issues=(),
    )


def _plate(
    index: int,
    *requirements: PrintPlanMaterialRequirement,
    ready: bool = True,
) -> PrintPlanPlate:
    return PrintPlanPlate(index, tuple(requirements), ready)


def _slot(
    slot_id: str,
    *,
    family: str | None = "PETG",
    presence: MaterialPresence = MaterialPresence.LOADED,
) -> MaterialSlotSnapshot:
    detected = None
    if family is not None:
        detected = DetectedMaterial(
            material_family=family,
            vendor_name=None,
            product_name=None,
            color=None,
            tag=None,
            remaining_fraction=None,
        )
    return MaterialSlotSnapshot(
        slot_id=slot_id,
        unit_id="unit:0",
        position=0 if slot_id == _SLOT_0 else 1,
        label=None,
        presence=presence,
        activity=MaterialActivity.UNKNOWN,
        detected_material=detected,
    )


def _material_system(
    *slots: MaterialSlotSnapshot,
    stale: bool = False,
    printer_id: str = _PRINTER_ID,
) -> MaterialSystemSnapshot:
    unit = MaterialUnitSnapshot(
        unit_id="unit:0",
        kind=MaterialUnitKind.MULTI_SLOT,
        label=None,
        position=0,
        slots=tuple(slots),
    )
    return MaterialSystemSnapshot(printer_id, (unit,), _NOW, stale)


def _topology(
    *routes: MaterialRouteSnapshot,
    toolheads: tuple[MaterialToolheadSnapshot, ...] | None = None,
    stale: bool = False,
    printer_id: str = _PRINTER_ID,
) -> MaterialTopologySnapshot:
    if toolheads is None:
        toolheads = (
            MaterialToolheadSnapshot(_TOOL_0, "Right", 0),
            MaterialToolheadSnapshot(_TOOL_1, "Left", 1),
        )
    return MaterialTopologySnapshot(printer_id, toolheads, tuple(routes), _NOW, stale)


def _fixed_route(slot_id: str, toolhead_id: str = _TOOL_0) -> MaterialRouteSnapshot:
    return MaterialRouteSnapshot(slot_id, (toolhead_id,), MaterialRouteKind.FIXED)


def _codes(result) -> set[MaterialRoutingBlockerCode]:
    return {blocker.code for blocker in result.blockers}


def test_single_plate_fixed_route_compiles_toolhead_identity() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(_fixed_route(_SLOT_0)),
    )

    assert result.eligible is True
    assert result.plate_index == 0
    assert result.blockers == ()
    assert result.bindings == (MaterialBinding(0, _SLOT_0, _TOOL_0),)


def test_expected_toolhead_position_selects_one_allowed_dynamic_route() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0, toolhead_position=1))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(
            MaterialRouteSnapshot(_SLOT_0, (_TOOL_0, _TOOL_1), MaterialRouteKind.DYNAMIC),
        ),
    )

    assert result.eligible is True
    assert result.bindings[0].toolhead_id == _TOOL_1


def test_expected_toolhead_must_be_reachable_from_explicit_source() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0, toolhead_position=1))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(_fixed_route(_SLOT_0, _TOOL_0)),
    )

    assert result.eligible is False
    assert result.bindings == ()
    assert _codes(result) == {MaterialRoutingBlockerCode.TOOLHEAD_INCOMPATIBLE}


def test_multi_plate_plan_requires_explicit_selection() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0)), _plate(1, _requirement(1))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(_fixed_route(_SLOT_0)),
    )

    assert result.eligible is False
    assert _codes(result) == {MaterialRoutingBlockerCode.PLATE_SELECTION_REQUIRED}


def test_explicit_plate_selection_scopes_required_materials() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0)), _plate(1, _requirement(1, family="PLA"))),
        selection=PrintArtifactSelection(plate_index=1),
        bindings=(MaterialBinding(1, _SLOT_1),),
        material_system=_material_system(_slot(_SLOT_1, family="PLA")),
        topology=_topology(_fixed_route(_SLOT_1, _TOOL_1)),
    )

    assert result.eligible is True
    assert result.plate_index == 1
    assert result.bindings == (MaterialBinding(1, _SLOT_1, _TOOL_1),)


def test_missing_and_extra_bindings_are_reported_without_partial_compilation() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0))),
        selection=None,
        bindings=(MaterialBinding(1, _SLOT_1),),
        material_system=_material_system(_slot(_SLOT_0), _slot(_SLOT_1)),
        topology=_topology(_fixed_route(_SLOT_0), _fixed_route(_SLOT_1)),
    )

    assert result.eligible is False
    assert result.bindings == ()
    assert _codes(result) == {
        MaterialRoutingBlockerCode.MATERIAL_BINDING_MISSING,
        MaterialRoutingBlockerCode.MATERIAL_BINDING_EXTRA,
    }


def test_stale_snapshots_block_compilation() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0), stale=True),
        topology=_topology(_fixed_route(_SLOT_0), stale=True),
    )

    assert result.eligible is False
    assert _codes(result) == {
        MaterialRoutingBlockerCode.MATERIAL_SYSTEM_STALE,
        MaterialRoutingBlockerCode.TOPOLOGY_STALE,
    }


def test_snapshots_from_different_printers_are_rejected() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(_fixed_route(_SLOT_0), printer_id="printer-2"),
    )

    assert result.eligible is False
    assert MaterialRoutingBlockerCode.SNAPSHOT_PRINTER_MISMATCH in _codes(result)


def test_unknown_or_unloaded_source_fails_closed() -> None:
    unknown = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_1)),
        topology=_topology(_fixed_route(_SLOT_0)),
    )
    unloaded = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0, presence=MaterialPresence.UNKNOWN)),
        topology=_topology(_fixed_route(_SLOT_0)),
    )

    assert _codes(unknown) == {MaterialRoutingBlockerCode.SOURCE_UNKNOWN}
    assert _codes(unloaded) == {MaterialRoutingBlockerCode.SOURCE_NOT_LOADED}


def test_known_material_family_must_match_but_color_is_not_a_hard_constraint() -> None:
    mismatch = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0, family="PETG"))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0, family="PLA")),
        topology=_topology(_fixed_route(_SLOT_0)),
    )
    color_agnostic = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0, family="PETG"))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0, family="petg")),
        topology=_topology(_fixed_route(_SLOT_0)),
    )

    assert _codes(mismatch) == {MaterialRoutingBlockerCode.MATERIAL_FAMILY_MISMATCH}
    assert color_agnostic.eligible is True


def test_required_family_with_unknown_detected_identity_is_blocked() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0, family="PETG"))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0, family=None)),
        topology=_topology(_fixed_route(_SLOT_0)),
    )

    assert _codes(result) == {MaterialRoutingBlockerCode.MATERIAL_IDENTITY_UNKNOWN}


def test_unknown_topology_route_is_blocked() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(MaterialRouteSnapshot(_SLOT_0, (), MaterialRouteKind.UNKNOWN)),
    )

    assert _codes(result) == {MaterialRoutingBlockerCode.ROUTE_UNKNOWN}


def test_missing_toolhead_expectation_requires_unambiguous_source_route() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0, toolhead_position=None))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(
            MaterialRouteSnapshot(_SLOT_0, (_TOOL_0, _TOOL_1), MaterialRouteKind.DYNAMIC),
        ),
    )

    assert _codes(result) == {MaterialRoutingBlockerCode.TOOLHEAD_AMBIGUOUS}


def test_expected_position_missing_from_topology_is_blocked() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0, toolhead_position=2))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(_fixed_route(_SLOT_0)),
    )

    assert _codes(result) == {MaterialRoutingBlockerCode.TOOLHEAD_UNKNOWN}


def test_existing_compiled_binding_is_idempotent_when_route_is_unchanged() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0, _TOOL_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(_fixed_route(_SLOT_0, _TOOL_0)),
    )

    assert result.eligible is True
    assert result.bindings == (MaterialBinding(0, _SLOT_0, _TOOL_0),)


def test_existing_compiled_binding_blocks_if_current_route_changes() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0))),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0, _TOOL_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(_fixed_route(_SLOT_0, _TOOL_1)),
    )

    assert result.eligible is False
    assert result.bindings == ()
    assert _codes(result) == {MaterialRoutingBlockerCode.COMPILED_ROUTE_CHANGED}


def test_blocked_print_plan_never_compiles() -> None:
    result = compile_material_routing(
        plan=_plan(_plate(0, _requirement(0), ready=False)),
        selection=None,
        bindings=(MaterialBinding(0, _SLOT_0),),
        material_system=_material_system(_slot(_SLOT_0)),
        topology=_topology(_fixed_route(_SLOT_0)),
    )

    assert _codes(result) == {MaterialRoutingBlockerCode.PRINT_PLAN_BLOCKED}
