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

  it('keeps printer cockpit keys aligned across EN, RU and UK', () => {
    const english = Object.keys(interfaceTranslations.en.translation.printerDetail).sort();
    expect(Object.keys(interfaceTranslations.ru.translation.printerDetail).sort()).toEqual(english);
    expect(Object.keys(interfaceTranslations.uk.translation.printerDetail).sort()).toEqual(english);
    expect(Object.keys(interfaceTranslations.ru.translation.printerDetail.telemetry).sort()).toEqual(
      Object.keys(interfaceTranslations.en.translation.printerDetail.telemetry).sort(),
    );
    expect(Object.keys(interfaceTranslations.uk.translation.printerDetail.diagnostics).sort()).toEqual(
      Object.keys(interfaceTranslations.en.translation.printerDetail.diagnostics).sort(),
    );
  });
});
