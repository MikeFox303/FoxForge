// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { afterEach, describe, expect, it, vi } from 'vitest';

import { addPrinter, loadPrinterConfigurations } from './printerSetupClient';

const fetchMock = vi.fn<typeof fetch>();

vi.stubGlobal('fetch', fetchMock);
vi.stubGlobal('crypto', { randomUUID: () => 'idem-123' });

afterEach(() => {
  fetchMock.mockReset();
});

describe('printer setup command client', () => {
  it('bootstraps an operator session and never sends printer credentials to the session endpoint', async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ accessToken: 'browser-token' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ apiVersion: '1', printers: [] }), { status: 200 }));

    await expect(loadPrinterConfigurations()).resolves.toEqual([]);

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/v1/operator-session', { method: 'POST' });
    const secondRequest = fetchMock.mock.calls[1];
    expect(secondRequest?.[0]).toBe('/api/v1/printers/configuration');
    const headers = secondRequest?.[1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer browser-token');
  });

  it('adds a Bambu printer with a fresh idempotency key and bearer token', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      configuration: {
        printerId: 'x2d-main',
        displayName: 'X2D',
        kind: 'bambu',
        vendor: 'bambu_lab',
        serialNumber: 'SERIAL',
        connection: { host: '192.0.2.5', accessCodeConfigured: true },
      },
      connection: 'connected',
      operationalState: 'idle',
      observedAt: '2026-09-04T12:00:00Z',
      reachable: true,
    }), { status: 201 }));

    const result = await addPrinter({
      printerId: 'x2d-main',
      displayName: 'X2D',
      kind: 'bambu',
      serialNumber: 'SERIAL',
      connection: { host: '192.0.2.5', accessCode: 'secret-code' },
    });

    expect(result.reachable).toBe(true);
    const request = fetchMock.mock.calls.at(-1);
    const headers = request?.[1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer browser-token');
    expect(headers.get('Idempotency-Key')).toBe('idem-123');
    expect(request?.[1]?.body).toContain('secret-code');
  });
});
