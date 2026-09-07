// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { printerSetupCopy } from './printerSetupCopy';

describe('printer setup localized copy', () => {
  it('keeps EN, RU and UK setup surfaces structurally identical', () => {
    const enKeys = Object.keys(printerSetupCopy.en).sort();
    expect(Object.keys(printerSetupCopy.ru).sort()).toEqual(enKeys);
    expect(Object.keys(printerSetupCopy.uk).sort()).toEqual(enKeys);
  });

  it('keeps verification wording explicit in every language', () => {
    for (const copy of Object.values(printerSetupCopy)) {
      expect(copy.verifyRequired.length).toBeGreaterThan(20);
      expect(copy.verified.length).toBeGreaterThan(20);
      expect(copy.test).not.toBe(copy.save);
    }
  });
});
