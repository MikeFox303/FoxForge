// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { alphaTranslations } from './alphaTranslations';
import { alphaTranslationExtras } from './alphaTranslationsExtra';

const pluralSuffix = /_(zero|one|two|few|many|other)$/;

function leafKeys(value: unknown, prefix = ''): string[] {
  if (typeof value === 'string') {
    expect(value.trim()).not.toBe('');
    return [prefix.replace(pluralSuffix, '')];
  }
  if (!value || typeof value !== 'object') return [];
  return Object.entries(value).flatMap(([key, child]) => leafKeys(child, prefix ? `${prefix}.${key}` : key));
}

function normalizedKeys(value: unknown): string[] {
  return [...new Set(leafKeys(value))].sort();
}

describe('alpha localization', () => {
  it('keeps the main alpha workspace keys aligned across EN, RU and UK', () => {
    const english = normalizedKeys(alphaTranslations.en.alpha);
    expect(normalizedKeys(alphaTranslations.ru.alpha)).toEqual(english);
    expect(normalizedKeys(alphaTranslations.uk.alpha)).toEqual(english);
  });

  it('keeps dynamic state/shell keys aligned across EN, RU and UK', () => {
    const english = normalizedKeys(alphaTranslationExtras.en.alpha);
    expect(normalizedKeys(alphaTranslationExtras.ru.alpha)).toEqual(english);
    expect(normalizedKeys(alphaTranslationExtras.uk.alpha)).toEqual(english);
  });
});
