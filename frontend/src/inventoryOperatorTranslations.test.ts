// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { inventoryOperatorTranslations } from './inventoryOperatorTranslations';

function keys(value: object, prefix = ''): string[] {
  return Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof child === 'object' && child !== null ? keys(child, path) : [path];
  }).sort();
}

describe('inventory operator translations', () => {
  it('keeps EN/RU/UK keys aligned', () => {
    const baseline = keys(inventoryOperatorTranslations.en);
    expect(keys(inventoryOperatorTranslations.ru)).toEqual(baseline);
    expect(keys(inventoryOperatorTranslations.uk)).toEqual(baseline);
  });
});
