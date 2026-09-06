// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import type { PrinterViewModel } from '../../domain';
import { fleetData } from '../../mockData';
import {
  hasJobControlCapability,
  materialSlots,
  printerByRouteId,
  printerDetailTabs,
  printerRoute,
  printerTelemetryPhase,
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

  it('does not present stale or disconnected telemetry as live', () => {
    const printer = fleetData.printers[0];
    expect(printerTelemetryPhase(printer)).toBe('live');
    expect(printerTelemetryPhase({ ...printer, snapshot: { ...printer.snapshot, stale: true } })).toBe('stale');
    expect(printerTelemetryPhase({ ...printer, snapshot: { ...printer.snapshot, connection: 'connecting' } })).toBe('connecting');
    expect(printerTelemetryPhase({ ...printer, snapshot: { ...printer.snapshot, connection: 'degraded' } })).toBe('degraded');
    expect(printerTelemetryPhase({ ...printer, snapshot: { ...printer.snapshot, connection: 'disconnected' } })).toBe('unavailable');
    expect(printerTelemetryPhase({ ...printer, snapshot: { ...printer.snapshot, operationalState: 'offline' } })).toBe('unavailable');
  });

  it('shows Control only when the typed job-control capability is advertised', () => {
    const printer = fleetData.printers[0];
    expect(hasJobControlCapability(printer)).toBe(false);
    expect(printerDetailTabs(printer)).toEqual(['overview', 'materials', 'queue', 'diagnostics']);

    const controllable: PrinterViewModel = {
      ...printer,
      capabilities: [
        ...printer.capabilities,
        {
          capabilityId: 'foxforge.job_control',
          majorVersion: 1,
          label: 'Job control',
          supportedActions: ['pause', 'cancel'],
        },
      ],
    };
    expect(hasJobControlCapability(controllable)).toBe(true);
    expect(printerDetailTabs(controllable)).toEqual(['overview', 'control', 'materials', 'queue', 'diagnostics']);
  });

  it('does not expose a Materials tab without a material capability snapshot', () => {
    const printer = fleetData.printers[1];
    const withoutMaterials: PrinterViewModel = { ...printer, materialSystem: undefined, materialTopology: undefined };
    expect(printerDetailTabs(withoutMaterials)).toEqual(['overview', 'queue', 'diagnostics']);
  });
});
