// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { fetchJson } from '../../data/apiClient';

export interface ReconnectDiagnostic {
  printerId: string;
  consecutiveFailures: number;
  lastAttemptAt?: string;
  lastFailureAt?: string;
  lastErrorCode?: string;
  lastErrorRetryable?: boolean;
  nextRetryAt?: string;
  recoveredAt?: string;
}

interface ApiReconnectDiagnostic {
  printerId: string;
  consecutiveFailures: number;
  lastAttemptAt: string | null;
  lastFailureAt: string | null;
  lastErrorCode: string | null;
  lastErrorRetryable: boolean | null;
  nextRetryAt: string | null;
  recoveredAt: string | null;
}

interface ApiReconnectDiagnosticsResponse {
  apiVersion: '1';
  printers: ApiReconnectDiagnostic[];
}

export async function loadReconnectDiagnostics(): Promise<ReconnectDiagnostic[]> {
  const response = await fetchJson<ApiReconnectDiagnosticsResponse>('/api/v1/diagnostics/reconnect');
  return response.printers.map(mapReconnectDiagnostic);
}

export function reconnectDiagnosticForPrinter(
  diagnostics: readonly ReconnectDiagnostic[],
  printerId: string,
): ReconnectDiagnostic | undefined {
  return diagnostics.find((item) => item.printerId === printerId);
}

function mapReconnectDiagnostic(item: ApiReconnectDiagnostic): ReconnectDiagnostic {
  return {
    printerId: item.printerId,
    consecutiveFailures: item.consecutiveFailures,
    lastAttemptAt: item.lastAttemptAt ?? undefined,
    lastFailureAt: item.lastFailureAt ?? undefined,
    lastErrorCode: item.lastErrorCode ?? undefined,
    lastErrorRetryable: item.lastErrorRetryable ?? undefined,
    nextRetryAt: item.nextRetryAt ?? undefined,
    recoveredAt: item.recoveredAt ?? undefined,
  };
}
