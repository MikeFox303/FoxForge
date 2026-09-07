// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import type { ThermalTelemetrySnapshot } from '../../domain';
import { temperatureLabel, thermalPresentation } from './thermalPresentation';

const telemetry: ThermalTelemetrySnapshot = {
  printerId: 'printer-1',
  observedAt: '2026-09-08T00:00:00Z',
  stale: false,
  zones: [
    { zoneId: 'chamber:0', kind: 'chamber', position: 30, currentCelsius: 34.2 },
    { zoneId: 'bed:0', kind: 'bed', position: 20, currentCelsius: 60, targetCelsius: 65 },
    { zoneId: 'hotend:1', kind: 'hotend', position: 1, label: 'Left hotend', currentCelsius: 219.6, targetCelsius: 220 },
    { zoneId: 'hotend:0', kind: 'hotend', position: 0, label: 'Right hotend', currentCelsius: 41, targetCelsius: 0 },
    { zoneId: 'other:empty', kind: 'other', position: 99 },
  ],
};

describe('thermalPresentation', () => {
  it('uses only typed common thermal zones and preserves deterministic operational order', () => {
    const presentation = thermalPresentation({ thermalTelemetry: telemetry });

    expect(presentation?.zones.map((zone) => zone.zoneId)).toEqual([
      'hotend:0',
      'hotend:1',
      'bed:0',
      'chamber:0',
    ]);
    expect(presentation?.stale).toBe(false);
  });

  it('returns no presentation when the printer does not advertise a thermal read model', () => {
    expect(thermalPresentation({})).toBeUndefined();
  });

  it('limits card density without mutating the source snapshot', () => {
    const presentation = thermalPresentation({ thermalTelemetry: telemetry }, 3);
    expect(presentation?.zones).toHaveLength(3);
    expect(telemetry.zones).toHaveLength(5);
  });

  it('keeps stale state explicit and formats temperatures compactly', () => {
    const presentation = thermalPresentation({ thermalTelemetry: { ...telemetry, stale: true } });
    expect(presentation?.stale).toBe(true);
    expect(temperatureLabel(219.6)).toBe('219.6°C');
    expect(temperatureLabel(60)).toBe('60°C');
    expect(temperatureLabel()).toBe('—');
  });
});
