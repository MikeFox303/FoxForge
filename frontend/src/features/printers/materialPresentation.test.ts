// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import type { MaterialUnitSnapshot } from '../../domain';
import { groupMaterialUnits } from './materialPresentation';

const unit = (unitId: string, kind: MaterialUnitSnapshot['kind'], position: number): MaterialUnitSnapshot => ({
  unitId,
  kind,
  position,
  slots: [],
});

describe('groupMaterialUnits', () => {
  it('separates multi-slot hardware from external feeds without vendor or model inference', () => {
    const groups = groupMaterialUnits([
      unit('ams-0', 'multi_slot', 0),
      unit('external-left', 'external', 1),
      unit('external-right', 'external', 2),
      unit('toolhead-source', 'toolhead', 3),
    ]);

    expect(groups.multiSlot.map((item) => item.unitId)).toEqual(['ams-0']);
    expect(groups.external.map((item) => item.unitId)).toEqual(['external-left', 'external-right']);
    expect(groups.other.map((item) => item.unitId)).toEqual(['toolhead-source']);
  });

  it('preserves backend-provided unit order within each presentation group', () => {
    const groups = groupMaterialUnits([
      unit('external-b', 'external', 2),
      unit('ams-b', 'multi_slot', 2),
      unit('external-a', 'external', 1),
      unit('ams-a', 'multi_slot', 1),
    ]);

    expect(groups.external.map((item) => item.unitId)).toEqual(['external-b', 'external-a']);
    expect(groups.multiSlot.map((item) => item.unitId)).toEqual(['ams-b', 'ams-a']);
  });
});
