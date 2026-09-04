// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { fleetData } from './mockData';
import {
  describeMaterialSource,
  findPrinter,
  fleetAvailability,
  formatDuration,
  formatPercent,
  formatRelativeTime,
  printerStatusLabel,
  summarizeFleet,
} from './viewModel';

describe('fleet presentation model', () => {
  it('distinguishes empty runtime collections from partially configured data', () => {
    expect(fleetAvailability({ printers: [], queue: [] })).toEqual({
      hasPrinters: false,
      hasQueueEntries: false,
      hasMaterialSystems: false,
    });
    expect(fleetAvailability({ printers: [], queue: fleetData.queue })).toEqual({
      hasPrinters: false,
      hasQueueEntries: true,
      hasMaterialSystems: false,
    });
  });

  it('summarizes the representative mixed fleet', () => {
    expect(summarizeFleet(fleetData)).toEqual({
      totalPrinters: 2,
      connectedPrinters: 2,
      printingPrinters: 1,
      queuedJobs: 2,
      materialAlerts: 1,
    });
  });

  it('formats durations and progress without vendor assumptions', () => {
    expect(formatDuration(2760)).toBe('46m');
    expect(formatDuration(5040)).toBe('1h 24m');
    expect(formatPercent(0.64)).toBe('64%');
  });

  it('formats snapshot freshness for user-facing printer views', () => {
    const now = Date.parse('2026-09-04T12:00:00Z');
    expect(formatRelativeTime('2026-09-04T11:59:40Z', now)).toBe('Updated just now');
    expect(formatRelativeTime('2026-09-04T11:52:00Z', now)).toBe('Updated 8m ago');
    expect(formatRelativeTime('2026-09-04T09:00:00Z', now)).toBe('Updated 3h ago');
  });

  it('derives printer state and material summaries from normalized snapshots', () => {
    const x2d = findPrinter(fleetData, 'bambu-x2d-main');
    const ender = findPrinter(fleetData, 'ender3-v3-ke');
    expect(x2d).toBeDefined();
    expect(ender).toBeDefined();
    expect(printerStatusLabel(x2d!)).toBe('printing');
    expect(describeMaterialSource(x2d!)).toBe('PETG · SUNLU');
    expect(describeMaterialSource(ender!)).toBe('PETG · SUNLU');
  });
});
