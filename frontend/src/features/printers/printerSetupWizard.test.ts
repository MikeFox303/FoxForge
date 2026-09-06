// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import type { PrinterSetupPayload } from '../../data/printerSetupClient';
import {
  canAdvancePrinterSetupStep,
  isPrinterSetupPayloadVerified,
  nextPrinterSetupStep,
  previousPrinterSetupStep,
  printerSetupPayloadFingerprint,
  printerSetupWizardSteps,
} from './printerSetupWizard';

const bambuPayload: PrinterSetupPayload = {
  printerId: 'bambu-01p00a000000001',
  displayName: 'X2D Main',
  kind: 'bambu',
  vendor: 'Bambu Lab',
  model: 'X2D',
  serialNumber: '01P00A000000001',
  connection: {
    host: '192.168.1.50',
    accessCode: '12345678',
  },
};

const moonrakerPayload: PrinterSetupPayload = {
  printerId: 'ender-ke',
  displayName: 'Ender KE',
  kind: 'moonraker',
  vendor: 'Creality',
  model: 'Ender-3 V3 KE',
  connection: {
    baseUrl: 'http://192.168.1.100:7125',
  },
};

describe('printer setup wizard contract', () => {
  it('keeps the approved staged flow in a stable order', () => {
    expect(printerSetupWizardSteps).toEqual(['provider', 'connection', 'identity', 'verify']);
    expect(nextPrinterSetupStep('provider')).toBe('connection');
    expect(nextPrinterSetupStep('verify')).toBe('verify');
    expect(previousPrinterSetupStep('verify')).toBe('identity');
    expect(previousPrinterSetupStep('provider')).toBe('provider');
  });

  it('requires Bambu connection credentials before leaving Connection', () => {
    expect(canAdvancePrinterSetupStep('connection', bambuPayload)).toBe(true);
    expect(canAdvancePrinterSetupStep('connection', {
      ...bambuPayload,
      connection: { ...bambuPayload.connection, accessCode: '' },
    })).toBe(false);
    expect(canAdvancePrinterSetupStep('connection', {
      ...bambuPayload,
      connection: { ...bambuPayload.connection, host: '' },
    })).toBe(false);
  });

  it('requires a usable Moonraker endpoint before leaving Connection', () => {
    expect(canAdvancePrinterSetupStep('connection', moonrakerPayload)).toBe(true);
    expect(canAdvancePrinterSetupStep('connection', {
      ...moonrakerPayload,
      connection: { baseUrl: 'http://' },
    })).toBe(false);
  });

  it('requires Bambu identity fields but keeps Moonraker vendor/model optional', () => {
    expect(canAdvancePrinterSetupStep('identity', bambuPayload)).toBe(true);
    expect(canAdvancePrinterSetupStep('identity', { ...bambuPayload, model: undefined })).toBe(false);
    expect(canAdvancePrinterSetupStep('identity', { ...bambuPayload, serialNumber: undefined })).toBe(false);
    expect(canAdvancePrinterSetupStep('identity', moonrakerPayload)).toBe(true);
    expect(canAdvancePrinterSetupStep('identity', { ...moonrakerPayload, vendor: undefined, model: undefined })).toBe(true);
  });

  it('binds verification to the exact normalized payload including credentials', () => {
    const fingerprint = printerSetupPayloadFingerprint(bambuPayload);
    expect(isPrinterSetupPayloadVerified(bambuPayload, fingerprint)).toBe(true);
    expect(isPrinterSetupPayloadVerified({
      ...bambuPayload,
      connection: { ...bambuPayload.connection, host: '192.168.1.51' },
    }, fingerprint)).toBe(false);
    expect(isPrinterSetupPayloadVerified({
      ...bambuPayload,
      connection: { ...bambuPayload.connection, accessCode: '87654321' },
    }, fingerprint)).toBe(false);
    expect(isPrinterSetupPayloadVerified({ ...bambuPayload, model: 'H2D' }, fingerprint)).toBe(false);
  });
});
