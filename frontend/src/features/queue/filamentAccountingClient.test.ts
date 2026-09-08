// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { afterEach, describe, expect, it, vi } from 'vitest';

import { clearOperatorSessionForTests, setOperatorCommandToken } from '../../data/commandClient';
import {
  loadFilamentAccounting,
  planQueueFilament,
  reconcileQueueFilament,
  releaseQueueFilament,
} from './filamentAccountingClient';

const fetchMock = vi.fn<typeof fetch>();
vi.stubGlobal('fetch', fetchMock);

afterEach(() => {
  fetchMock.mockReset();
  clearOperatorSessionForTests();
});

const reservation = {
  queueId: 'queue-1',
  materialIndex: 0,
  spoolId: 'spool-1',
  printerId: 'printer-1',
  slotId: 'slot-0',
  estimatedMassG: '25.50',
  actualMassG: null,
  state: 'reserved',
  createdAt: '2026-09-08T00:00:00Z',
  updatedAt: '2026-09-08T00:00:00Z',
  note: null,
} as const;

describe('filament accounting client', () => {
  it('loads the normalized accounting snapshot', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      apiVersion: '1',
      reservations: [reservation],
      spools: [{ spoolId: 'spool-1', reservedMassG: '25.50', availableMassG: '774.50' }],
    }), { status: 200 }));

    const snapshot = await loadFilamentAccounting();
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/v1/filament-accounting');
    expect(snapshot.reservations[0]).toMatchObject({
      queueId: 'queue-1',
      estimatedMassG: '25.50',
      actualMassG: undefined,
    });
  });

  it('plans exact gram strings against material indices only', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      apiVersion: '1', queueId: 'queue-1', reservations: [reservation], replayed: false,
    }), { status: 201 }));

    await planQueueFilament(
      'queue-1',
      [{ materialIndex: 0, estimatedMassG: '25.50' }],
      'plan-key-1',
    );

    const [, options] = fetchMock.mock.calls[0]!;
    const headers = options?.headers as Headers;
    expect(headers.get('Authorization')).toContain('Bearer operator-token');
    expect(headers.get('Idempotency-Key')).toBe('plan-key-1');
    expect(JSON.parse(String(options?.body))).toEqual({
      estimates: [{ materialIndex: 0, estimatedMassG: '25.50' }],
    });
    expect(String(options?.body)).not.toContain('slotId');
    expect(String(options?.body)).not.toContain('toolheadId');
  });

  it('releases a durable queue plan without inventing a request body', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      apiVersion: '1', queueId: 'queue-1', reservations: [], replayed: false,
    }), { status: 200 }));

    await releaseQueueFilament('queue-1', 'release-key-1');

    const [, options] = fetchMock.mock.calls[0]!;
    expect(options?.method).toBe('POST');
    expect(options?.body).toBeUndefined();
    expect((options?.headers as Headers).get('Idempotency-Key')).toBe('release-key-1');
  });

  it('sends explicit actual mass and optional note for reconciliation', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      apiVersion: '1', queueId: 'queue-1', reservations: [reservation], replayed: false,
    }), { status: 200 }));

    await reconcileQueueFilament('queue-1', 0, '12.75', ' weighed ', 'reconcile-key-1');

    const [, options] = fetchMock.mock.calls[0]!;
    expect(JSON.parse(String(options?.body))).toEqual({
      materialIndex: 0,
      actualMassG: '12.75',
      note: 'weighed',
    });
    expect((options?.headers as Headers).get('Idempotency-Key')).toBe('reconcile-key-1');
  });
});
