// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { afterEach, describe, expect, it, vi } from 'vitest';

import { loadReconnectDiagnostics, reconnectDiagnosticForPrinter } from './reconnectDiagnosticsClient';

const fetchMock = vi.fn<typeof fetch>();
vi.stubGlobal('fetch', fetchMock);

afterEach(() => {
  fetchMock.mockReset();
});

describe('reconnect diagnostics client', () => {
  it('loads the normalized read model and converts null fields to optional values', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      apiVersion: '1',
      printers: [
        {
          printerId: 'x2d-main',
          consecutiveFailures: 2,
          lastAttemptAt: '2026-09-06T00:00:15Z',
          lastFailureAt: '2026-09-06T00:00:15Z',
          lastErrorCode: 'authentication_failed',
          lastErrorRetryable: false,
          nextRetryAt: '2026-09-06T00:00:30Z',
          recoveredAt: null,
        },
        {
          printerId: 'ender-ke',
          consecutiveFailures: 0,
          lastAttemptAt: null,
          lastFailureAt: null,
          lastErrorCode: null,
          lastErrorRetryable: null,
          nextRetryAt: null,
          recoveredAt: null,
        },
      ],
    }), { status: 200 }));

    const diagnostics = await loadReconnectDiagnostics();

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/diagnostics/reconnect', {
      headers: { Accept: 'application/json' },
    });
    expect(diagnostics[0]).toEqual({
      printerId: 'x2d-main',
      consecutiveFailures: 2,
      lastAttemptAt: '2026-09-06T00:00:15Z',
      lastFailureAt: '2026-09-06T00:00:15Z',
      lastErrorCode: 'authentication_failed',
      lastErrorRetryable: false,
      nextRetryAt: '2026-09-06T00:00:30Z',
      recoveredAt: undefined,
    });
    expect(diagnostics[1]).toEqual({
      printerId: 'ender-ke',
      consecutiveFailures: 0,
      lastAttemptAt: undefined,
      lastFailureAt: undefined,
      lastErrorCode: undefined,
      lastErrorRetryable: undefined,
      nextRetryAt: undefined,
      recoveredAt: undefined,
    });
  });

  it('selects diagnostics by stable FoxForge printer id', () => {
    const diagnostics = [
      { printerId: 'x2d-main', consecutiveFailures: 1 },
      { printerId: 'ender-ke', consecutiveFailures: 0 },
    ];

    expect(reconnectDiagnosticForPrinter(diagnostics, 'ender-ke')).toEqual({
      printerId: 'ender-ke',
      consecutiveFailures: 0,
    });
    expect(reconnectDiagnosticForPrinter(diagnostics, 'missing')).toBeUndefined();
  });

  it('surfaces HTTP failures instead of inventing reconnect state', async () => {
    fetchMock.mockResolvedValueOnce(new Response('', { status: 503, statusText: 'Service Unavailable' }));

    await expect(loadReconnectDiagnostics()).rejects.toThrow('FoxForge API request failed: 503 Service Unavailable');
  });
});
