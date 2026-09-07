// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type {
  MaterialRouteSnapshot,
  MaterialToolheadSnapshot,
  MaterialTopologySnapshot,
  MaterialUnitSnapshot,
  PrinterViewModel,
} from '../../domain';

export interface MaterialUnitGroups {
  multiSlot: MaterialUnitSnapshot[];
  external: MaterialUnitSnapshot[];
  other: MaterialUnitSnapshot[];
}

export interface MaterialRoutePresentation {
  route: MaterialRouteSnapshot;
  toolheads: MaterialToolheadSnapshot[];
  unresolved: boolean;
  warning: boolean;
}

export function groupMaterialUnits(units: MaterialUnitSnapshot[]): MaterialUnitGroups {
  const groups: MaterialUnitGroups = { multiSlot: [], external: [], other: [] };
  for (const unit of units) {
    if (unit.kind === 'multi_slot') groups.multiSlot.push(unit);
    else if (unit.kind === 'external') groups.external.push(unit);
    else groups.other.push(unit);
  }
  return groups;
}

export function materialRouteForSlot(
  printer: Pick<PrinterViewModel, 'materialTopology'>,
  slotId: string,
): MaterialRoutePresentation | undefined {
  const topology = printer.materialTopology;
  if (!topology) return undefined;
  const route = topology.routes.find((candidate) => candidate.sourceSlotId === slotId);
  return route ? resolveMaterialRoute(topology, route) : undefined;
}

export function resolveMaterialRoute(
  topology: MaterialTopologySnapshot,
  route: MaterialRouteSnapshot,
): MaterialRoutePresentation {
  const toolheads = route.toolheadIds
    .map((toolheadId) => topology.toolheads.find((toolhead) => toolhead.toolheadId === toolheadId))
    .filter((toolhead): toolhead is MaterialToolheadSnapshot => toolhead !== undefined);
  const unresolved = route.toolheadIds.length === 0 || toolheads.length !== route.toolheadIds.length;
  return {
    route,
    toolheads,
    unresolved,
    warning: topology.stale || route.kind === 'unknown' || unresolved,
  };
}
