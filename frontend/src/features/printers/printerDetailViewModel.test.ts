// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { fleetData } from '../../mockData';
import {
  materialSlots,
  printerByRouteId,
  printerRoute,
  queueForPrinter,
  summarizePrinterMaterials,
} from './printerDetailViewModel';

describe('printer detail presentation model', () => {
  it('resolves printers from URL-safe route ids', () => {
    const route = printerRoute('bambu-x2d-main');
    expect(route).toBe('/printers/bambu-x2d-main');
    expect(printerByRouteId(fleetData, route.split('/').pop())?.identity.displayName).toBe('X2D Main');
  });

  it('keeps printer queue selection vendor-neutral', () => {
    const entries = queueForPrinter(fleetData, 'bambu-x2d-main');
    expect(entries).toHaveLength(2);
    expect(entries.map((entry) => entry.state)).toEqual(['accepted', 'blocked']);
  });

  it('summarizes material slots without parsing vendor slot ids', () => {
    const printer = fleetData.printers[0];
    expect(materialSlots(printer).map((slot) => slot.slotId)).toEqual(['ams-1-a1', 'ams-1-a2', 'ams-1-a3', 'ams-1-a4']);
    expect(summarizePrinterMaterials(printer)).toEqual({
      loadedSlots: 3,
      activeSlots: 1,
      lowSlots: 1,
      totalSlots: 4,
    });
  });
});
