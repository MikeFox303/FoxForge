// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { afterEach, describe, expect, it, vi } from 'vitest';

import { clearOperatorSessionForTests, setOperatorCommandToken } from '../../data/commandClient';
import {
  createQueueJobIdentity,
  dispatchPrintJob,
  enqueuePrintJob,
  inspectArtifactPrintPlan,
  sha256File,
  stagePrintArtifact,
} from './queueCommandClient';

const fetchMock = vi.fn<typeof fetch>();
let uuidCounter = 0;

vi.stubGlobal('fetch', fetchMock);
vi.stubGlobal('crypto', {
  randomUUID: () => `00000000-0000-4000-8000-${String(++uuidCounter).padStart(12, '0')}`,
  subtle: {
    digest: async (_algorithm: string, data: ArrayBuffer) => {
      const bytes = new Uint8Array(data);
      if (bytes.length === 3 && bytes[0] === 97 && bytes[1] === 98 && bytes[2] === 99) {
        return Uint8Array.from([
          0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
          0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
          0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
          0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad,
        ]).buffer;
      }
      throw new Error('unexpected digest input');
    },
  },
});

afterEach(() => {
  fetchMock.mockReset();
  clearOperatorSessionForTests();
  uuidCounter = 0;
});

describe('queue command client', () => {
  it('creates stable queue identities without coupling them to one HTTP dispatch attempt', () => {
    const identity = createQueueJobIdentity();
    expect(identity.queueId).not.toBe(identity.dispatchId);
    expect(identity.enqueueIdempotencyKey).not.toBe(identity.queueId);
    expect(identity).not.toHaveProperty('dispatchIdempotencyKey');
  });

  it('computes the browser SHA-256 digest used by artifact staging', async () => {
    await expect(sha256File(new Blob(['abc']))).resolves.toBe(
      'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    );
  });

  it('stages bytes without sending a client filesystem path', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      artifactId: 'a'.repeat(64),
      filename: 'part.gcode',
      format: 'gcode',
      sizeBytes: 3,
      sha256: 'a'.repeat(64),
      replayed: false,
    }), { status: 201 }));

    const file = new File(['abc'], 'part.gcode', { type: 'text/plain' });
    await stagePrintArtifact(file, 'a'.repeat(64));

    const request = fetchMock.mock.calls[0];
    const headers = request?.[1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer operator-token-0123456789abcdef0123456789');
    expect(headers.get('X-FoxForge-Filename')).toBe('part.gcode');
    expect(request?.[1]?.body).toBe(file);
    expect(JSON.stringify(request?.[1])).not.toContain('C:\\');
  });

  it('reads the immutable staged 3mf print plan through the authenticated queue boundary', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      artifactId: 'b'.repeat(64),
      artifactSha256: 'b'.repeat(64),
      readyForRouting: true,
      plates: [{ plateIndex: 1, readyForRouting: true, materialRequirements: [] }],
      issues: [],
    }), { status: 200 }));

    const plan = await inspectArtifactPrintPlan('b'.repeat(64));

    expect(plan.readyForRouting).toBe(true);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(`/api/v1/artifacts/${'b'.repeat(64)}/print-plan`);
    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer operator-token-0123456789abcdef0123456789');
  });

  it('sends only operator material source intent and never a client toolhead decision', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      queueId: 'queue-1', printerId: 'x2d', state: 'pending',
    }), { status: 201 }));

    const identity = {
      queueId: '153b6d90-5bb1-49fd-b90a-4316ba57db88',
      dispatchId: 'b9132e98-22d5-43ae-8d4f-f52c72bc921e',
      enqueueIdempotencyKey: 'enqueue-fixed',
    };
    await enqueuePrintJob({
      identity,
      printerId: 'x2d',
      artifactId: 'a'.repeat(64),
      requestedName: 'Dual material part',
      plateIndex: 2,
      materialBindings: [
        { materialIndex: 0, slotId: 'bambu:unit:0:tray:0' },
        { materialIndex: 1, slotId: 'bambu:external:255' },
      ],
    });

    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body)) as Record<string, unknown>;
    expect(body.selection).toEqual({ plateIndex: 2 });
    expect(body.materialBindings).toEqual([
      { materialIndex: 0, slotId: 'bambu:unit:0:tray:0' },
      { materialIndex: 1, slotId: 'bambu:external:255' },
    ]);
    expect(JSON.stringify(body)).not.toContain('toolheadId');
  });

  it('keeps queue dispatchId stable while the caller controls each HTTP dispatch idempotency key', async () => {
    setOperatorCommandToken('operator-token-0123456789abcdef0123456789');
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({
        queueId: 'queue-1', printerId: 'x2d', state: 'pending',
      }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        queueId: 'queue-1', printerId: 'x2d', state: 'blocked',
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        queueId: 'queue-1', printerId: 'x2d', state: 'accepted',
      }), { status: 200 }));

    const identity = {
      queueId: '153b6d90-5bb1-49fd-b90a-4316ba57db88',
      dispatchId: 'b9132e98-22d5-43ae-8d4f-f52c72bc921e',
      enqueueIdempotencyKey: 'enqueue-fixed',
    };
    await enqueuePrintJob({ identity, printerId: 'x2d', artifactId: 'a'.repeat(64), requestedName: 'Part' });
    await dispatchPrintJob(identity.queueId, 'dispatch-attempt-1');
    await dispatchPrintJob(identity.queueId, 'dispatch-attempt-2');

    const enqueueRequest = fetchMock.mock.calls[0];
    const enqueueHeaders = enqueueRequest?.[1]?.headers as Headers;
    expect(enqueueHeaders.get('Idempotency-Key')).toBe('enqueue-fixed');
    expect(enqueueRequest?.[1]?.body).toContain(identity.dispatchId);

    const firstDispatchHeaders = fetchMock.mock.calls[1]?.[1]?.headers as Headers;
    const secondDispatchHeaders = fetchMock.mock.calls[2]?.[1]?.headers as Headers;
    expect(firstDispatchHeaders.get('Idempotency-Key')).toBe('dispatch-attempt-1');
    expect(secondDispatchHeaders.get('Idempotency-Key')).toBe('dispatch-attempt-2');
  });
});
