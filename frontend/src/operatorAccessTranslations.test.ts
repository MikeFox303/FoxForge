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

  it('explains the Umbrel app-password credential source without embedding a secret', () => {
    for (const language of ['en', 'ru', 'uk'] as const) {
      const help = operatorAccessTranslations[language].credentialHelp;
      expect(help).toContain('Umbrel');
      expect(help).toContain('FOXFORGE_COMMAND_TOKEN');
      expect(help).not.toMatch(/[A-Fa-f0-9]{32,}/);
    }
  });
});
