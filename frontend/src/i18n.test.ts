// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { interfaceTranslations } from './i18n';

describe('shared interface localization', () => {
  it('keeps inventory keys aligned across EN, RU and UK', () => {
    const english = Object.keys(interfaceTranslations.en.translation.inventory).sort();
    expect(Object.keys(interfaceTranslations.ru.translation.inventory).sort()).toEqual(english);
    expect(Object.keys(interfaceTranslations.uk.translation.inventory).sort()).toEqual(english);
  });
});
