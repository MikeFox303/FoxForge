// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { buildFilamentPlan, type FilamentPlanRow } from './FilamentPlanEditor';

const row = (rowId: string, slotId: string, estimatedMassG: string): FilamentPlanRow => ({
  rowId,
  slotId,
  estimatedMassG,
});

describe('buildFilamentPlan', () => {
  it('preserves exact decimal strings and assigns stable sequential material indices', () => {
    expect(buildFilamentPlan([
      row('a', 'ams:0', '12.50'),
      row('b', 'ams:3', '3.125'),
    ])).toEqual({
      materialBindings: [
        { materialIndex: 0, slotId: 'ams:0' },
        { materialIndex: 1, slotId: 'ams:3' },
      ],
      estimates: [
        { materialIndex: 0, estimatedMassG: '12.50' },
        { materialIndex: 1, estimatedMassG: '3.125' },
      ],
    });
  });

  it('rejects incomplete or non-positive plans', () => {
    expect(buildFilamentPlan([row('a', '', '12')])).toBeNull();
    expect(buildFilamentPlan([row('a', 'slot-0', '0')])).toBeNull();
    expect(buildFilamentPlan([row('a', 'slot-0', '')])).toBeNull();
  });
});
