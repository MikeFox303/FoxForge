// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { MaterialUnitSnapshot } from '../../domain';

export interface MaterialUnitGroups {
  multiSlot: MaterialUnitSnapshot[];
  external: MaterialUnitSnapshot[];
  other: MaterialUnitSnapshot[];
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
