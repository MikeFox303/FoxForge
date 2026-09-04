// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { operatorAccessTranslations } from './operatorAccessTranslations';

function keys(value: Record<string, string>): string[] {
  return Object.keys(value).sort();
}

describe('operator access translations', () => {
  it('keeps EN/RU/UK keys aligned', () => {
    expect(keys(operatorAccessTranslations.ru)).toEqual(keys(operatorAccessTranslations.en));
    expect(keys(operatorAccessTranslations.uk)).toEqual(keys(operatorAccessTranslations.en));
  });
});
