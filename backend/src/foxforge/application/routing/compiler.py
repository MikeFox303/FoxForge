# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Fail-closed compilation of logical print materials into physical routes.

The compiler is vendor-neutral application logic. It joins immutable print-plan
requirements with an operator's explicit source-slot bindings and current
material/topology snapshots. It never chooses a source slot automatically and
never invokes a printer side effect.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from foxforge.application.artifacts import ArtifactPrintPlan, PrintPlanMaterialRequirement, PrintPlanPlate
from foxforge.domain.printers.capabilities import (
    MaterialBinding,
    MaterialPresence,
    MaterialRouteKind,
    MaterialSlotSnapshot,
    MaterialSystemSnapshot,
    MaterialTopologySnapshot,
    MaterialToolheadSnapshot,
    PrintArtifactSelection,
)


class MaterialRoutingBlockerCode(StrEnum):
    PLATE_SELECTION_REQUIRED = "plate_selection_required"
    PLATE_NOT_FOUND = "plate_not_found"
    PRINT_PLAN_BLOCKED = "print_plan_blocked"
    MATERIAL_BINDING_MISSING = "material_binding_missing"
    MATERIAL_BINDING_EXTRA = "material_binding_extra"
    SNAPSHOT_PRINTER_MISMATCH = "snapshot_printer_mismatch"
    MATERIAL_SYSTEM_STALE = "material_system_stale"
    TOPOLOGY_STALE = "topology_stale"
    SOURCE_UNKNOWN = "source_unknown"
    SOURCE_NOT_LOADED = "source_not_loaded"
    MATERIAL_IDENTITY_UNKNOWN = "material_identity_unknown"
    MATERIAL_FAMILY_MISMATCH = "material_family_mismatch"
    ROUTE_UNKNOWN = "route_unknown"
    TOOLHEAD_UNKNOWN = "toolhead_unknown"
    TOOLHEAD_AMBIGUOUS = "toolhead_ambiguous"
    TOOLHEAD_INCOMPATIBLE = "toolhead_incompatible"
    COMPILED_ROUTE_CHANGED = "compiled_route_changed"


@dataclass(frozen=True, slots=True)
class MaterialRoutingBlocker:
    code: MaterialRoutingBlockerCode
    message: str
    material_index: int | None = None
    slot_id: str | None = None

    def __post_init__(self) -> None:
        if not self.message:
            raise ValueError("material routing blocker message must not be empty")
        if self.material_index is not None and self.material_index < 0:
            raise ValueError("material_index must be non-negative when present")


@dataclass(frozen=True, slots=True)
class MaterialRoutingCompilation:
    plate_index: int | None
    bindings: tuple[MaterialBinding, ...]
    blockers: tuple[MaterialRoutingBlocker, ...]

    def __post_init__(self) -> None:
        if self.plate_index is not None and self.plate_index < 0:
            raise ValueError("plate_index must be non-negative when present")
        if self.blockers and self.bindings:
            raise ValueError("blocked routing compilation must not expose partial compiled bindings")
        if not self.blockers and self.plate_index is None:
            raise ValueError("eligible routing compilation must resolve one plate")
        indices = [binding.material_index for binding in self.bindings]
        if indices != sorted(indices) or len(indices) != len(set(indices)):
            raise ValueError("compiled material bindings must have unique sorted material indices")

    @property
    def eligible(self) -> bool:
        return not self.blockers


def compile_material_routing(
    *,
    plan: ArtifactPrintPlan,
    selection: PrintArtifactSelection | None,
    bindings: tuple[MaterialBinding, ...],
    material_system: MaterialSystemSnapshot,
    topology: MaterialTopologySnapshot,
) -> MaterialRoutingCompilation:
    """Compile explicit source bindings into immutable source -> toolhead routes.

    The function is intentionally all-or-nothing. Any unknown, stale,
    contradictory or incomplete evidence returns blockers and no compiled
    bindings. It never guesses a source slot, material family or toolhead.
    """

    plate, plate_blocker = _selected_plate(plan, selection)
    if plate_blocker is not None:
        return _blocked(None, plate_blocker)
    assert plate is not None

    if not plate.ready_for_routing:
        return _blocked(
            plate.plate_index,
            MaterialRoutingBlocker(
                MaterialRoutingBlockerCode.PRINT_PLAN_BLOCKED,
                f"plate {plate.plate_index} is not ready for material routing",
            ),
        )

    blockers: list[MaterialRoutingBlocker] = []
    required = {item.material_index: item for item in plate.material_requirements}
    supplied = {item.material_index: item for item in bindings}

    for material_index in sorted(required.keys() - supplied.keys()):
        blockers.append(
            MaterialRoutingBlocker(
                MaterialRoutingBlockerCode.MATERIAL_BINDING_MISSING,
                f"material {material_index} has no explicit physical source binding",
                material_index=material_index,
            )
        )
    for material_index in sorted(supplied.keys() - required.keys()):
        binding = supplied[material_index]
        blockers.append(
            MaterialRoutingBlocker(
                MaterialRoutingBlockerCode.MATERIAL_BINDING_EXTRA,
                f"material {material_index} is not used by selected plate {plate.plate_index}",
                material_index=material_index,
                slot_id=binding.slot_id,
            )
        )

    if material_system.printer_id != topology.printer_id:
        blockers.append(
            MaterialRoutingBlocker(
                MaterialRoutingBlockerCode.SNAPSHOT_PRINTER_MISMATCH,
                "material-system and topology snapshots belong to different printers",
            )
        )
    if material_system.stale:
        blockers.append(
            MaterialRoutingBlocker(
                MaterialRoutingBlockerCode.MATERIAL_SYSTEM_STALE,
                "material-system snapshot is stale",
            )
        )
    if topology.stale:
        blockers.append(
            MaterialRoutingBlocker(
                MaterialRoutingBlockerCode.TOPOLOGY_STALE,
                "material-topology snapshot is stale",
            )
        )
    if blockers:
        return MaterialRoutingCompilation(plate.plate_index, (), tuple(blockers))

    slots = _material_slots(material_system)
    routes = {route.source_slot_id: route for route in topology.routes}
    toolheads_by_position = _toolheads_by_position(topology)
    compiled: list[MaterialBinding] = []

    for material_index in sorted(required):
        requirement = required[material_index]
        binding = supplied[material_index]
        slot = slots.get(binding.slot_id)
        if slot is None:
            blockers.append(
                _material_blocker(
                    MaterialRoutingBlockerCode.SOURCE_UNKNOWN,
                    f"physical source {binding.slot_id!r} is not present in current material-system snapshot",
                    requirement,
                    binding,
                )
            )
            continue

        source_blocker = _validate_source(requirement, binding, slot)
        if source_blocker is not None:
            blockers.append(source_blocker)
            continue

        route = routes.get(binding.slot_id)
        if route is None or route.kind == MaterialRouteKind.UNKNOWN or not route.toolhead_ids:
            blockers.append(
                _material_blocker(
                    MaterialRoutingBlockerCode.ROUTE_UNKNOWN,
                    f"physical source {binding.slot_id!r} has no proven toolhead route",
                    requirement,
                    binding,
                )
            )
            continue

        resolved_toolhead, route_blocker = _resolve_toolhead(
            requirement,
            binding,
            route.toolhead_ids,
            toolheads_by_position,
        )
        if route_blocker is not None:
            blockers.append(route_blocker)
            continue
        assert resolved_toolhead is not None

        if binding.toolhead_id is not None and binding.toolhead_id != resolved_toolhead.toolhead_id:
            blockers.append(
                _material_blocker(
                    MaterialRoutingBlockerCode.COMPILED_ROUTE_CHANGED,
                    (
                        f"material {material_index} was compiled for {binding.toolhead_id!r}, "
                        f"but current evidence resolves to {resolved_toolhead.toolhead_id!r}"
                    ),
                    requirement,
                    binding,
                )
            )
            continue

        compiled.append(replace(binding, toolhead_id=resolved_toolhead.toolhead_id))

    if blockers:
        return MaterialRoutingCompilation(plate.plate_index, (), tuple(blockers))
    return MaterialRoutingCompilation(plate.plate_index, tuple(compiled), ())


def _selected_plate(
    plan: ArtifactPrintPlan,
    selection: PrintArtifactSelection | None,
) -> tuple[PrintPlanPlate | None, MaterialRoutingBlocker | None]:
    explicit_index = selection.plate_index if selection is not None else None
    if explicit_index is not None:
        for plate in plan.plates:
            if plate.plate_index == explicit_index:
                return plate, None
        return None, MaterialRoutingBlocker(
            MaterialRoutingBlockerCode.PLATE_NOT_FOUND,
            f"selected plate {explicit_index} is not present in immutable print plan",
        )

    if len(plan.plates) == 1:
        return plan.plates[0], None
    if not plan.plates:
        return None, MaterialRoutingBlocker(
            MaterialRoutingBlockerCode.PLATE_NOT_FOUND,
            "immutable print plan does not contain a printable plate",
        )
    return None, MaterialRoutingBlocker(
        MaterialRoutingBlockerCode.PLATE_SELECTION_REQUIRED,
        "multi-plate print plan requires an explicit plate selection",
    )


def _material_slots(snapshot: MaterialSystemSnapshot) -> dict[str, MaterialSlotSnapshot]:
    return {slot.slot_id: slot for unit in snapshot.units for slot in unit.slots}


def _toolheads_by_position(snapshot: MaterialTopologySnapshot) -> dict[int, tuple[MaterialToolheadSnapshot, ...]]:
    result: dict[int, list[MaterialToolheadSnapshot]] = {}
    for toolhead in snapshot.toolheads:
        result.setdefault(toolhead.position, []).append(toolhead)
    return {position: tuple(items) for position, items in result.items()}


def _validate_source(
    requirement: PrintPlanMaterialRequirement,
    binding: MaterialBinding,
    slot: MaterialSlotSnapshot,
) -> MaterialRoutingBlocker | None:
    if slot.presence != MaterialPresence.LOADED:
        return _material_blocker(
            MaterialRoutingBlockerCode.SOURCE_NOT_LOADED,
            f"physical source {binding.slot_id!r} is not confirmed loaded ({slot.presence.value})",
            requirement,
            binding,
        )

    expected_family = _material_family(requirement.material_family)
    if expected_family is None:
        return None
    detected = slot.detected_material
    actual_family = None if detected is None else _material_family(detected.material_family)
    if actual_family is None:
        return _material_blocker(
            MaterialRoutingBlockerCode.MATERIAL_IDENTITY_UNKNOWN,
            f"physical source {binding.slot_id!r} does not report a material family",
            requirement,
            binding,
        )
    if actual_family != expected_family:
        return _material_blocker(
            MaterialRoutingBlockerCode.MATERIAL_FAMILY_MISMATCH,
            (
                f"material {requirement.material_index} requires {requirement.material_family!r}, "
                f"but source {binding.slot_id!r} reports {detected.material_family!r}"
            ),
            requirement,
            binding,
        )
    return None


def _resolve_toolhead(
    requirement: PrintPlanMaterialRequirement,
    binding: MaterialBinding,
    route_toolhead_ids: tuple[str, ...],
    toolheads_by_position: dict[int, tuple[MaterialToolheadSnapshot, ...]],
) -> tuple[MaterialToolheadSnapshot | None, MaterialRoutingBlocker | None]:
    expected_position = requirement.expected_toolhead_position
    if expected_position is not None:
        matches = toolheads_by_position.get(expected_position, ())
        if not matches:
            return None, _material_blocker(
                MaterialRoutingBlockerCode.TOOLHEAD_UNKNOWN,
                f"print plan expects toolhead position {expected_position}, which printer topology does not report",
                requirement,
                binding,
            )
        if len(matches) != 1:
            return None, _material_blocker(
                MaterialRoutingBlockerCode.TOOLHEAD_AMBIGUOUS,
                f"toolhead position {expected_position} is ambiguous in current topology",
                requirement,
                binding,
            )
        target = matches[0]
        if target.toolhead_id not in route_toolhead_ids:
            return None, _material_blocker(
                MaterialRoutingBlockerCode.TOOLHEAD_INCOMPATIBLE,
                (
                    f"source {binding.slot_id!r} cannot reach print-plan toolhead "
                    f"{target.toolhead_id!r} at position {expected_position}"
                ),
                requirement,
                binding,
            )
        return target, None

    if len(route_toolhead_ids) != 1:
        return None, _material_blocker(
            MaterialRoutingBlockerCode.TOOLHEAD_AMBIGUOUS,
            (
                f"print plan does not identify a toolhead for material {requirement.material_index}, "
                f"and source {binding.slot_id!r} can reach {len(route_toolhead_ids)} toolheads"
            ),
            requirement,
            binding,
        )

    only_id = route_toolhead_ids[0]
    for toolheads in toolheads_by_position.values():
        for toolhead in toolheads:
            if toolhead.toolhead_id == only_id:
                return toolhead, None
    return None, _material_blocker(
        MaterialRoutingBlockerCode.TOOLHEAD_UNKNOWN,
        f"route references unknown toolhead {only_id!r}",
        requirement,
        binding,
    )


def _material_blocker(
    code: MaterialRoutingBlockerCode,
    message: str,
    requirement: PrintPlanMaterialRequirement,
    binding: MaterialBinding,
) -> MaterialRoutingBlocker:
    return MaterialRoutingBlocker(
        code,
        message,
        material_index=requirement.material_index,
        slot_id=binding.slot_id,
    )


def _material_family(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _blocked(plate_index: int | None, blocker: MaterialRoutingBlocker) -> MaterialRoutingCompilation:
    return MaterialRoutingCompilation(plate_index, (), (blocker,))
