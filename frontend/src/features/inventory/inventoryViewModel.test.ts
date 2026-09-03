// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { fleetData } from '../../mockData';
import { inventoryData } from './mockInventory';
import { assignmentLabel, formatMass, remainingFraction, summarizeInventory } from './inventoryViewModel';

describe('inventory presentation model', () => {
  it('summarizes active inventory without counting archived spools', () => {
    expect(summarizeInventory(inventoryData)).toEqual({
      activeSpools: 5,
      assignedSpools: 4,
      lowSpools: 1,
      remainingMassG: 2463,
    });
  });

  it('preserves decimal strings at the DTO boundary and derives display values locally', () => {
    const spool = inventoryData.spools[0];
    expect(spool.remainingFilamentMassG).toBe('612');
    expect(remainingFraction(spool)).toBeCloseTo(0.612);
    expect(formatMass('2463')).toBe('2.46 kg');
  });

  it('resolves opaque assignments through the fleet material snapshot', () => {
    expect(assignmentLabel(inventoryData.spools[0], fleetData)).toBe('X2D Main · A1');
    expect(assignmentLabel(inventoryData.spools[4], fleetData)).toBe('Storage');
  });
});
