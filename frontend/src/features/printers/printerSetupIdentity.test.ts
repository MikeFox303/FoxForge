// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { normalizeBambuSerial, stableBambuPrinterId } from './printerSetupIdentity';

describe('Bambu setup identity', () => {
  it('normalizes serials for case-sensitive Bambu MQTT topics', () => {
    expect(normalizeBambuSerial(' 01p00abc123 ')).toBe('01P00ABC123');
  });

  it('derives a stable local printer id from the immutable serial', () => {
    expect(stableBambuPrinterId('01P00ABC123')).toBe('bambu-01p00abc123');
    expect(stableBambuPrinterId(' 01p00abc123 ')).toBe('bambu-01p00abc123');
  });

  it('never emits characters outside the backend printer-id contract', () => {
    const id = stableBambuPrinterId('SN / TEST : 01');
    expect(id).toMatch(/^[A-Za-z0-9._-]{1,64}$/);
    expect(id).toBe('bambu-sn-test-01');
  });

  it('returns empty when no usable serial is available', () => {
    expect(stableBambuPrinterId('   ')).toBe('');
  });
});
