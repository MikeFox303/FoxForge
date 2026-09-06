# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Callable

from foxforge.domain.printers import PrinterId
from foxforge.domain.printers.capabilities import (
    MATERIAL_TOPOLOGY_CAPABILITY_ID,
    MATERIAL_TOPOLOGY_MAJOR_VERSION,
    MaterialRouteKind,
    MaterialRouteSnapshot,
    MaterialToolheadSnapshot,
    MaterialTopologyDescriptor,
    MaterialTopologySnapshot,
)

from .mapping import bambu_slot_id
from .native import BambuMaterialUnitKind, BambuNativeState


class BambuMaterialTopologyCapability:
    """Expose proven Bambu material-source routing without leaking wire fields."""

    def __init__(self, printer_id: PrinterId, native_snapshot: Callable[[], BambuNativeState]) -> None:
        self._printer_id = printer_id
        self._native_snapshot = native_snapshot
        self._descriptor = MaterialTopologyDescriptor(
            capability_id=MATERIAL_TOPOLOGY_CAPABILITY_ID,
            major_version=MATERIAL_TOPOLOGY_MAJOR_VERSION,
            reports_dynamic_routes=False,
        )

    @property
    def descriptor(self) -> MaterialTopologyDescriptor:
        return self._descriptor

    def snapshot(self) -> MaterialTopologySnapshot:
        return map_bambu_material_topology(self._printer_id, self._native_snapshot())


def map_bambu_material_topology(printer_id: PrinterId, native: BambuNativeState) -> MaterialTopologySnapshot:
    dual_external = _has_dual_external(native)
    routes: list[MaterialRouteSnapshot] = []
    referenced_toolheads: set[int] = set()

    for unit in native.material_units:
        if unit.kind == BambuMaterialUnitKind.EXTERNAL:
            target = _external_extruder(unit.ams_id) if dual_external else None
        else:
            target = unit.routed_extruder_id

        for tray in unit.trays:
            source_slot_id = bambu_slot_id(tray.ams_id, tray.tray_id)
            if target in {0, 1}:
                referenced_toolheads.add(target)
                routes.append(
                    MaterialRouteSnapshot(
                        source_slot_id=source_slot_id,
                        toolhead_ids=(_toolhead_id(target),),
                        kind=MaterialRouteKind.FIXED,
                    )
                )
            else:
                routes.append(
                    MaterialRouteSnapshot(
                        source_slot_id=source_slot_id,
                        toolhead_ids=(),
                        kind=MaterialRouteKind.UNKNOWN,
                    )
                )

    toolheads = tuple(
        MaterialToolheadSnapshot(
            toolhead_id=_toolhead_id(extruder_id),
            label=_toolhead_label(extruder_id),
            position=extruder_id,
        )
        for extruder_id in sorted(referenced_toolheads)
    )
    return MaterialTopologySnapshot(
        printer_id=printer_id,
        toolheads=toolheads,
        routes=tuple(routes),
        observed_at=native.observed_at,
        stale=not native.connected,
    )


def _has_dual_external(native: BambuNativeState) -> bool:
    external_ids = {unit.ams_id for unit in native.material_units if unit.kind == BambuMaterialUnitKind.EXTERNAL}
    return 254 in external_ids and 255 in external_ids


def _external_extruder(ams_id: int) -> int | None:
    if ams_id == 254:
        return 1
    if ams_id == 255:
        return 0
    return None


def _toolhead_id(extruder_id: int) -> str:
    return f"bambu:toolhead:{extruder_id}"


def _toolhead_label(extruder_id: int) -> str:
    if extruder_id == 1:
        return "Left toolhead"
    if extruder_id == 0:
        return "Right toolhead"
    return f"Toolhead {extruder_id}"
