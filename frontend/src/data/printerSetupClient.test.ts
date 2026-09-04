// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  CommandAuthenticationRequiredError,
  clearOperatorSessionForTests,
  setOperatorCommandToken,
} from './commandClient';
import { addPrinter, loadPrinterConfigurations } from './printerSetupClient';

const fetchMock = vi.fn<typeof fetch>();

vi.stubGlobal('fetch', fetchMock);
vi.stubGlobal('crypto', { randomUUID: () => 'idem-123' });

afterEach(() => {
  fetchMock.mockReset();
  clearOperatorSessionForTests();
});

describe('printer setup command client', () => {
  it('fails closed before network access when this tab has no operator token', async () => {
    await expect(loadPrinterConfigurations()).rejects.toBeInstanceOf(CommandAuthenticationRequiredError);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('uses only the in-memory operator token for authenticated reads', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ apiVersion: '1', printers: [] }), { status: 200 }));

    await expect(loadPrinterConfigurations()).resolves.toEqual([]);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const request = fetchMock.mock.calls[0];
    expect(request?.[0]).toBe('/api/v1/printers/configuration');
    const headers = request?.[1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer operator-token-0123456789abcdef0123456789');
  });

  it('adds a Bambu printer with a fresh idempotency key and bearer token', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
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
    expect(headers.get('Authorization')).toBe('Bearer operator-token-0123456789abcdef0123456789');
    expect(headers.get('Idempotency-Key')).toBe('idem-123');
    expect(request?.[1]?.body).toContain('secret-code');
  });

  it('clears the in-memory operator token after a 401 response', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: 'unauthorized' } }), { status: 401 }));

    await expect(loadPrinterConfigurations()).rejects.toMatchObject({ status: 401 });
    await expect(loadPrinterConfigurations()).rejects.toBeInstanceOf(CommandAuthenticationRequiredError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
