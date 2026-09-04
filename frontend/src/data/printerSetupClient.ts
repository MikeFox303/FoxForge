// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

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

let browserToken: string | null = null;
let sessionPromise: Promise<string> | null = null;

export async function ensureOperatorSession(): Promise<string> {
  if (browserToken) return browserToken;
  if (sessionPromise) return sessionPromise;

  sessionPromise = (async () => {
    const response = await fetch('/api/v1/operator-session', { method: 'POST' });
    const payload = await response.json().catch(() => null) as unknown;
    if (!response.ok) throw apiError(response.status, payload);
    if (!isRecord(payload) || typeof payload.accessToken !== 'string') {
      throw new Error('FoxForge returned an invalid operator-session response.');
    }
    browserToken = payload.accessToken;
    return browserToken;
  })();

  try {
    return await sessionPromise;
  } finally {
    sessionPromise = null;
  }
}

export async function loadPrinterConfigurations(): Promise<PrinterConfigurationView[]> {
  const payload = await authenticatedJson('/api/v1/printers/configuration');
  if (!isRecord(payload) || !Array.isArray(payload.printers)) throw new Error('Invalid printer configuration response.');
  return payload.printers as PrinterConfigurationView[];
}

export async function testPrinterConnection(payload: PrinterSetupPayload): Promise<PrinterSetupOutcome> {
  return authenticatedJson('/api/v1/printers/test-connection', { method: 'POST', json: payload }) as Promise<PrinterSetupOutcome>;
}

export async function addPrinter(payload: PrinterSetupPayload): Promise<PrinterSetupOutcome> {
  return authenticatedJson('/api/v1/printers', {
    method: 'POST',
    json: payload,
    idempotencyKey: crypto.randomUUID(),
  }) as Promise<PrinterSetupOutcome>;
}

export async function reconnectPrinter(printerId: string): Promise<PrinterSetupOutcome> {
  return authenticatedJson(`/api/v1/printers/${encodeURIComponent(printerId)}/reconnect`, {
    method: 'POST',
    idempotencyKey: crypto.randomUUID(),
  }) as Promise<PrinterSetupOutcome>;
}

export async function removePrinter(printerId: string): Promise<void> {
  await authenticatedJson(`/api/v1/printers/${encodeURIComponent(printerId)}`, {
    method: 'DELETE',
    idempotencyKey: crypto.randomUUID(),
  });
}

async function authenticatedJson(
  path: string,
  options: { method?: string; json?: object; idempotencyKey?: string } = {},
): Promise<any> {
  const token = await ensureOperatorSession();
  const headers = new Headers({ Authorization: `Bearer ${token}` });
  if (options.json) headers.set('Content-Type', 'application/json');
  if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey);

  const response = await fetch(path, {
    method: options.method ?? 'GET',
    headers,
    body: options.json ? JSON.stringify(options.json) : undefined,
  });
  const payload = await response.json().catch(() => null) as unknown;
  if (response.status === 401) {
    browserToken = null;
  }
  if (!response.ok) throw apiError(response.status, payload);
  return payload;
}

function apiError(status: number, payload: unknown): Error {
  if (isRecord(payload) && isRecord(payload.error) && typeof payload.error.message === 'string') {
    return new Error(payload.error.message);
  }
  return new Error(`FoxForge API request failed (${status}).`);
}

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === 'object' && value !== null;
}
