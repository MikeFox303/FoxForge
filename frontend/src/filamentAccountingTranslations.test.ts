// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { filamentAccountingTranslations } from './filamentAccountingTranslations';

function keys(value: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return child && typeof child === 'object' && !Array.isArray(child)
      ? keys(child as Record<string, unknown>, path)
      : [path];
  }).sort();
}

describe('filament accounting translations', () => {
  it('keeps EN/RU/UK key parity', () => {
    const english = keys(filamentAccountingTranslations.en as unknown as Record<string, unknown>);
    expect(keys(filamentAccountingTranslations.ru as unknown as Record<string, unknown>)).toEqual(english);
    expect(keys(filamentAccountingTranslations.uk as unknown as Record<string, unknown>)).toEqual(english);
  });

  it('states the safety boundaries explicitly in every language', () => {
    for (const language of ['en', 'ru', 'uk'] as const) {
      const copy = filamentAccountingTranslations[language];
      expect(copy.boundary.length).toBeGreaterThan(20);
      expect(copy.estimateHint.length).toBeGreaterThan(20);
      expect(copy.actualMassHint.length).toBeGreaterThan(20);
      expect(copy.confirmRelease.length).toBeGreaterThan(20);
    }
    expect(filamentAccountingTranslations.en.boundary.toLowerCase()).toContain('never guesses grams');
    expect(filamentAccountingTranslations.en.actualMassHint.toLowerCase()).toContain('progress percentage');
    expect(filamentAccountingTranslations.en.confirmRelease.toLowerCase()).toContain('terminal');
  });
});
