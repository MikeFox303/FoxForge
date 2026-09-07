// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { thermalTelemetryTranslations } from './thermalTelemetryTranslations';

function keys(value: object): string[] {
  return Object.keys(value).sort();
}

describe('thermal telemetry translations', () => {
  it('keeps EN/RU/UK top-level and zone-kind keys aligned', () => {
    expect(keys(thermalTelemetryTranslations.ru)).toEqual(keys(thermalTelemetryTranslations.en));
    expect(keys(thermalTelemetryTranslations.uk)).toEqual(keys(thermalTelemetryTranslations.en));
    expect(keys(thermalTelemetryTranslations.ru.kinds)).toEqual(keys(thermalTelemetryTranslations.en.kinds));
    expect(keys(thermalTelemetryTranslations.uk.kinds)).toEqual(keys(thermalTelemetryTranslations.en.kinds));
  });
});
