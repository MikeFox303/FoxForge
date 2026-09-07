// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { TFunction } from 'i18next';
import { describe, expect, it } from 'vitest';

import type { PrinterViewModel } from '../../domain';
import { printerStatusTranslationKey, relativeTimeLabel } from './printerPresentation';

const basePrinter: PrinterViewModel = {
  identity: {
    printerId: 'printer-1',
    displayName: 'Printer',
    vendor: 'Example',
    adapterKind: 'example',
  },
  snapshot: {
    printerId: 'printer-1',
    connection: 'connected',
    operationalState: 'idle',
    observedAt: '2026-09-08T00:00:00Z',
    stale: false,
    faultSummary: [],
  },
  capabilities: [],
};

const t = ((key: string, options?: { count?: number }) => (
  options?.count === undefined ? key : `${key}:${options.count}`
)) as unknown as TFunction;

describe('printer presentation primitives', () => {
  it('prioritizes stale state over connection and operational state', () => {
    expect(printerStatusTranslationKey({
      ...basePrinter,
      snapshot: { ...basePrinter.snapshot, connection: 'disconnected', stale: true },
    })).toBe('stale');
  });

  it('uses connection state before operational state when not connected', () => {
    expect(printerStatusTranslationKey({
      ...basePrinter,
      snapshot: { ...basePrinter.snapshot, connection: 'degraded' },
    })).toBe('degraded');
  });

  it('uses operational state for a fresh connected printer', () => {
    expect(printerStatusTranslationKey(basePrinter)).toBe('idle');
  });

  it('formats relative time through translation keys and handles future timestamps safely', () => {
    const now = Date.parse('2026-09-08T01:00:00Z');
    expect(relativeTimeLabel('2026-09-08T00:59:40Z', t, now)).toBe('alpha.relative.justNow');
    expect(relativeTimeLabel('2026-09-08T00:45:00Z', t, now)).toBe('alpha.relative.minutes:15');
    expect(relativeTimeLabel('2026-09-07T22:00:00Z', t, now)).toBe('alpha.relative.hours:3');
    expect(relativeTimeLabel('2026-09-06T01:00:00Z', t, now)).toBe('alpha.relative.days:2');
    expect(relativeTimeLabel('2026-09-08T02:00:00Z', t, now)).toBe('alpha.relative.justNow');
    expect(relativeTimeLabel('invalid', t, now)).toBe('alpha.relative.recently');
  });
});
