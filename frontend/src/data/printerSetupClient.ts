// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { authenticatedCommandJson, ensureOperatorSession } from './commandClient';

export type PrinterSetupKind = 'bambu' | 'moonraker';

export interface PrinterSetupPayload {
  printerId: string;
  displayName: string;
  kind: PrinterSetupKind;
  vendor?: string;
  model?: string;
  serialNumber?: string;
  connection: {
    host?: string;
    accessCode?: string;
    baseUrl?: string;
    apiKey?: string;
  };
}

export interface PrinterConfigurationView {
  printerId: string;
  displayName: string;
  kind: PrinterSetupKind;
  vendor: string;
  model?: string | null;
  serialNumber?: string | null;
  connection: {
    host?: string;
    accessCodeConfigured?: boolean;
    baseUrl?: string;
    apiKeyConfigured?: boolean;
  };
}

export interface PrinterSetupOutcome {
  configuration: PrinterConfigurationView;
  connection: string;
  operationalState: string;
  observedAt: string;
  reachable: boolean;
  connectionError?: {
    code: string;
    message: string;
    retryable: boolean;
    vendorCode?: string | null;
  } | null;
}

export { ensureOperatorSession };

export async function loadPrinterConfigurations(): Promise<PrinterConfigurationView[]> {
  const payload = await authenticatedCommandJson<unknown>('/api/v1/printers/configuration');
  if (!isRecord(payload) || !Array.isArray(payload.printers)) {
    throw new Error('Invalid printer configuration response.');
  }
  return payload.printers as PrinterConfigurationView[];
}

export async function testPrinterConnection(payload: PrinterSetupPayload): Promise<PrinterSetupOutcome> {
  return authenticatedCommandJson<PrinterSetupOutcome>('/api/v1/printers/test-connection', {
    method: 'POST',
    json: payload,
  });
}

export async function addPrinter(payload: PrinterSetupPayload): Promise<PrinterSetupOutcome> {
  return authenticatedCommandJson<PrinterSetupOutcome>('/api/v1/printers', {
    method: 'POST',
    json: payload,
    idempotencyKey: crypto.randomUUID(),
  });
}

export async function reconnectPrinter(printerId: string): Promise<PrinterSetupOutcome> {
  return authenticatedCommandJson<PrinterSetupOutcome>(
    `/api/v1/printers/${encodeURIComponent(printerId)}/reconnect`,
    {
      method: 'POST',
      idempotencyKey: crypto.randomUUID(),
    },
  );
}

export async function removePrinter(printerId: string): Promise<void> {
  await authenticatedCommandJson(`/api/v1/printers/${encodeURIComponent(printerId)}`, {
    method: 'DELETE',
    idempotencyKey: crypto.randomUUID(),
  });
}

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === 'object' && value !== null;
}
