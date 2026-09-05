// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { bambuModelGroups, isKnownBambuModel } from './bambuModels';

describe('Bambu model catalog', () => {
  it('keeps the current setup picker grouped by product series', () => {
    expect(bambuModelGroups).toEqual([
      { series: 'A1 Series', models: ['A1', 'A1 Mini'] },
      { series: 'A2 Series', models: ['A2L'] },
      { series: 'H2 Series', models: ['H2C', 'H2D', 'H2D Pro', 'H2S'] },
      { series: 'P Series', models: ['P1P', 'P1S', 'P2S'] },
      { series: 'X1 Series', models: ['X1', 'X1 Carbon', 'X1E'] },
      { series: 'X2 Series', models: ['X2D'] },
    ]);
  });

  it('recognizes known models while allowing future discovered models as fallbacks', () => {
    expect(isKnownBambuModel('X2D')).toBe(true);
    expect(isKnownBambuModel(' H2D Pro ')).toBe(true);
    expect(isKnownBambuModel('Future Model')).toBe(false);
  });
});
