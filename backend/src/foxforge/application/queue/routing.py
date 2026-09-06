# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Queue-facing integration for fail-closed material routing compilation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from foxforge.application.artifacts import PrintPlanInspectionError, inspect_print_plan
from foxforge.application.fleet import FleetService
from foxforge.application.routing import MaterialRoutingBlocker, MaterialRoutingBlockerCode, compile_material_routing
from foxforge.domain.printers.capabilities import (
    MaterialSystemCapability,
    MaterialTopologyCapability,
    PrintArtifactFormat,
    PrintAssessmentBlocker,
    PrintAssessmentBlockerCode,
    PrintExecutionCapability,
    PrintExecutionRequest,
)


@dataclass(frozen=True, slots=True)
class QueueRoutingPreparation:
    request: PrintExecutionRequest
    blockers: tuple[PrintAssessmentBlocker, ...] = ()

    @property
    def eligible(self) -> bool:
        return not self.blockers


def prepare_queue_routing(
    fleet: FleetService,
    *,
    printer_id: str,
    request: PrintExecutionRequest,
    print_execution: PrintExecutionCapability,
) -> QueueRoutingPreparation:
    """Compile a queue request only when its execution contract requires 3MF routing.

    G-code and print-execution capabilities that do not support material bindings
    keep their existing path. A routed 3MF request is returned with compiler-owned
    ``toolhead_id`` values only when all immutable and live evidence agrees.
    """

    if not _requires_material_routing(request, print_execution):
        return QueueRoutingPreparation(request)

    material_system = fleet.capability(printer_id, MaterialSystemCapability)
    material_topology = fleet.capability(printer_id, MaterialTopologyCapability)
    if material_system is None or material_topology is None:
        return QueueRoutingPreparation(
            request,
            (
                PrintAssessmentBlocker(
                    PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                    "3MF material routing requires current material-system and topology capabilities",
                ),
            ),
        )

    try:
        plan = inspect_print_plan(request.artifact)
    except PrintPlanInspectionError as error:
        return QueueRoutingPreparation(
            request,
            (
                PrintAssessmentBlocker(
                    PrintAssessmentBlockerCode.UNSUPPORTED_ARTIFACT,
                    f"3MF routing evidence could not be inspected safely: {error}",
                ),
            ),
        )

    compilation = compile_material_routing(
        plan=plan,
        selection=request.selection,
        bindings=request.material_bindings,
        material_system=material_system.snapshot(),
        topology=material_topology.snapshot(),
    )
    if not compilation.eligible:
        return QueueRoutingPreparation(
            request,
            tuple(_assessment_blocker(blocker) for blocker in compilation.blockers),
        )

    return QueueRoutingPreparation(
        replace(request, material_bindings=compilation.bindings),
    )


def _requires_material_routing(
    request: PrintExecutionRequest,
    print_execution: PrintExecutionCapability,
) -> bool:
    return (
        request.artifact.format == PrintArtifactFormat.THREE_MF
        and print_execution.descriptor.supports_material_bindings
    )


def _assessment_blocker(blocker: MaterialRoutingBlocker) -> PrintAssessmentBlocker:
    if blocker.code in {
        MaterialRoutingBlockerCode.PLATE_SELECTION_REQUIRED,
        MaterialRoutingBlockerCode.PLATE_NOT_FOUND,
    }:
        code = PrintAssessmentBlockerCode.UNSUPPORTED_SELECTION
    elif blocker.code == MaterialRoutingBlockerCode.PRINT_PLAN_BLOCKED:
        code = PrintAssessmentBlockerCode.UNSUPPORTED_ARTIFACT
    elif blocker.code in {
        MaterialRoutingBlockerCode.SNAPSHOT_PRINTER_MISMATCH,
        MaterialRoutingBlockerCode.MATERIAL_SYSTEM_STALE,
        MaterialRoutingBlockerCode.TOPOLOGY_STALE,
        MaterialRoutingBlockerCode.SOURCE_UNKNOWN,
        MaterialRoutingBlockerCode.SOURCE_NOT_LOADED,
    }:
        code = PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE
    else:
        code = PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID
    return PrintAssessmentBlocker(code, blocker.message)
