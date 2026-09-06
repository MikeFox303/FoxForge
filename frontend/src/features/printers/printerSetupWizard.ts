// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { PrinterSetupPayload } from '../../data/printerSetupClient';

export type PrinterSetupWizardStep = 'provider' | 'connection' | 'identity' | 'verify';

export const printerSetupWizardSteps: readonly PrinterSetupWizardStep[] = [
  'provider',
  'connection',
  'identity',
  'verify',
];

export function nextPrinterSetupStep(step: PrinterSetupWizardStep): PrinterSetupWizardStep {
  const index = printerSetupWizardSteps.indexOf(step);
  return printerSetupWizardSteps[Math.min(index + 1, printerSetupWizardSteps.length - 1)];
}

export function previousPrinterSetupStep(step: PrinterSetupWizardStep): PrinterSetupWizardStep {
  const index = printerSetupWizardSteps.indexOf(step);
  return printerSetupWizardSteps[Math.max(index - 1, 0)];
}

export function canAdvancePrinterSetupStep(
  step: PrinterSetupWizardStep,
  payload: PrinterSetupPayload,
): boolean {
  if (step === 'provider') return true;

  if (step === 'connection') {
    if (payload.kind === 'bambu') {
      return Boolean(payload.connection.host?.trim() && payload.connection.accessCode?.trim());
    }
    return usableMoonrakerBaseUrl(payload.connection.baseUrl);
  }

  if (step === 'identity') {
    if (!payload.printerId.trim() || !payload.displayName.trim()) return false;
    if (payload.kind === 'bambu') {
      return Boolean(payload.model?.trim() && payload.serialNumber?.trim());
    }
    return true;
  }

  return false;
}

export function printerSetupPayloadFingerprint(payload: PrinterSetupPayload): string {
  return JSON.stringify({
    printerId: payload.printerId,
    displayName: payload.displayName,
    kind: payload.kind,
    vendor: payload.vendor ?? null,
    model: payload.model ?? null,
    serialNumber: payload.serialNumber ?? null,
    connection: payload.kind === 'bambu'
      ? {
          host: payload.connection.host ?? null,
          accessCode: payload.connection.accessCode ?? null,
        }
      : {
          baseUrl: payload.connection.baseUrl ?? null,
          apiKey: payload.connection.apiKey ?? null,
        },
  });
}

export function isPrinterSetupPayloadVerified(
  payload: PrinterSetupPayload,
  verifiedFingerprint: string | null,
): boolean {
  return verifiedFingerprint !== null && verifiedFingerprint === printerSetupPayloadFingerprint(payload);
}

function usableMoonrakerBaseUrl(value?: string): boolean {
  const normalized = value?.trim() ?? '';
  return normalized.length > 0 && normalized !== 'http://' && normalized !== 'https://';
}
