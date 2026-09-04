// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { jobControlTranslations } from './jobControlTranslations';

function keys(value: object, prefix = ''): string[] {
  return Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof child === 'object' && child !== null ? keys(child, path) : [path];
  }).sort();
}

describe('job-control translations', () => {
  it('keeps EN/RU/UK key parity', () => {
    const english = keys(jobControlTranslations.en);
    expect(keys(jobControlTranslations.ru)).toEqual(english);
    expect(keys(jobControlTranslations.uk)).toEqual(english);
  });
});
