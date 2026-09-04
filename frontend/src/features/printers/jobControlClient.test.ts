// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { afterEach, describe, expect, it, vi } from 'vitest';

import { clearOperatorSessionForTests } from '../../data/commandClient';
import { controlPrinterJob, createJobControlIdentity } from './jobControlClient';

const fetchMock = vi.fn<typeof fetch>();
let uuidCounter = 0;

vi.stubGlobal('fetch', fetchMock);
vi.stubGlobal('crypto', {
  randomUUID: () => `00000000-0000-4000-8000-${String(++uuidCounter).padStart(12, '0')}`,
});

afterEach(() => {
  fetchMock.mockReset();
  clearOperatorSessionForTests();
  uuidCounter = 0;
});

describe('job-control client', () => {
  it('keeps logical control identity separate from HTTP idempotency identity', () => {
    const identity = createJobControlIdentity();
    expect(identity.controlId).not.toBe(identity.idempotencyKey);
  });

  it('sends the verified vendor job identity and caller-owned idempotency key', async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ accessToken: 'browser-token' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        controlId: 'control-1',
        printerId: 'x2d',
        action: 'pause',
        vendorJobId: 'vendor-job-1',
        accepted: true,
        replayed: false,
      }), { status: 200 }));

    await controlPrinterJob({
      identity: { controlId: 'control-1', idempotencyKey: 'http-command-1' },
      printerId: 'x2d',
      vendorJobId: 'vendor-job-1',
      action: 'pause',
    });

    const request = fetchMock.mock.calls[1];
    expect(request?.[0]).toBe('/api/v1/printers/x2d/job-control');
    const headers = request?.[1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer browser-token');
    expect(headers.get('Idempotency-Key')).toBe('http-command-1');
    expect(JSON.parse(request?.[1]?.body as string)).toEqual({
      controlId: 'control-1',
      action: 'pause',
      expectedVendorJobId: 'vendor-job-1',
    });
  });
});
