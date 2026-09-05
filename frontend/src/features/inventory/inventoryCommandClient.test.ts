// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { afterEach, describe, expect, it, vi } from 'vitest';

import { clearOperatorSessionForTests, setOperatorCommandToken } from '../../data/commandClient';
import { archiveSpool, createSpool, moveSpool, unassignSpool } from './inventoryCommandClient';

const fetchMock = vi.fn<typeof fetch>();
vi.stubGlobal('fetch', fetchMock);

afterEach(() => {
  fetchMock.mockReset();
  clearOperatorSessionForTests();
});

describe('inventory command client', () => {
  it('sends exact decimal strings with caller-owned idempotency keys', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ spoolId: 'spool-1' }), { status: 201 }));

    await createSpool({
      spoolId: '20fdc5cb-7af3-4c3d-8f50-a97ff26c02f5',
      materialFamily: 'PETG',
      initialFilamentMassG: '1000.000',
      emptySpoolMassG: '180.50',
    }, 'inventory-create-fixed');

    const [, options] = fetchMock.mock.calls[0];
    const headers = options?.headers as Headers;
    expect(headers.get('Idempotency-Key')).toBe('inventory-create-fixed');
    expect(headers.get('Authorization')).toContain('operator-token');
    expect(options?.body).toContain('"initialFilamentMassG":"1000.000"');
    expect(options?.body).toContain('"emptySpoolMassG":"180.50"');
  });

  it('uses opaque printer slot IDs without translating them', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }));

    await moveSpool('spool-id', 'x2d-main', 'bambu:unit:0:tray:3', 'move-fixed');

    const [, options] = fetchMock.mock.calls[0];
    expect(options?.method).toBe('PUT');
    expect(options?.body).toBe(JSON.stringify({ printerId: 'x2d-main', slotId: 'bambu:unit:0:tray:3' }));
  });

  it('keeps unassign and archive as distinct idempotent commands', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock
      .mockResolvedValueOnce(new Response('{}', { status: 200 }))
      .mockResolvedValueOnce(new Response('{}', { status: 200 }));

    await unassignSpool('spool-id', 'unassign-fixed');
    await archiveSpool('spool-id', 'archive-fixed');

    expect(fetchMock.mock.calls[0]?.[1]?.method).toBe('DELETE');
    expect((fetchMock.mock.calls[0]?.[1]?.headers as Headers).get('Idempotency-Key')).toBe('unassign-fixed');
    expect(fetchMock.mock.calls[1]?.[1]?.method).toBe('POST');
    expect((fetchMock.mock.calls[1]?.[1]?.headers as Headers).get('Idempotency-Key')).toBe('archive-fixed');
  });
});
