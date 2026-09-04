// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { filamentAccountingTranslations } from './filamentAccountingTranslations';

function keys(value: unknown, prefix = ''): string[] {
  if (typeof value !== 'object' || value === null) return [prefix];
  return Object.entries(value).flatMap(([key, child]) => keys(child, prefix ? `${prefix}.${key}` : key));
}

describe('filament accounting translations', () => {
  it('keeps EN/RU/UK keys in parity', () => {
    const expected = keys(filamentAccountingTranslations.en).sort();
    expect(keys(filamentAccountingTranslations.ru).sort()).toEqual(expected);
    expect(keys(filamentAccountingTranslations.uk).sort()).toEqual(expected);
  });
});
