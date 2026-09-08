// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { afterEach, describe, expect, it, vi } from 'vitest';

import { loadQueueFromApi } from './apiClient';

const fetchMock = vi.fn<typeof fetch>();

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe('queue API mapping', () => {
  it('preserves persisted source and compiler-owned toolhead routing evidence', async () => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      apiVersion: '1',
      entries: [{
        queueId: '153b6d90-5bb1-49fd-b90a-4316ba57db88',
        printerId: 'bambu-x2d-main',
        state: 'pending',
        createdAt: '2026-09-08T05:00:00Z',
        updatedAt: '2026-09-08T05:00:00Z',
        attemptCount: 0,
        request: {
          requestedName: 'Dual material part',
          artifact: { filename: 'part.3mf', format: '3mf' },
          materialBindings: [
            {
              materialIndex: 0,
              slotId: 'bambu:external:255',
              toolheadId: 'bambu:toolhead:0',
            },
            {
              materialIndex: 1,
              slotId: 'bambu:unit:0:tray:0',
              toolheadId: null,
            },
          ],
        },
        assessment: null,
        error: null,
      }],
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    const queue = await loadQueueFromApi();

    expect(queue[0]?.materialBindings).toEqual([
      {
        materialIndex: 0,
        slotId: 'bambu:external:255',
        toolheadId: 'bambu:toolhead:0',
      },
      {
        materialIndex: 1,
        slotId: 'bambu:unit:0:tray:0',
        toolheadId: undefined,
      },
    ]);
  });

  it('keeps an explicit empty binding list instead of inventing routing', async () => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      apiVersion: '1',
      entries: [{
        queueId: '253b6d90-5bb1-49fd-b90a-4316ba57db89',
        printerId: 'moonraker-main',
        state: 'pending',
        createdAt: '2026-09-08T05:00:00Z',
        updatedAt: '2026-09-08T05:00:00Z',
        attemptCount: 0,
        request: {
          requestedName: null,
          artifact: { filename: 'part.gcode', format: 'gcode' },
          materialBindings: [],
        },
        assessment: null,
        error: null,
      }],
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    const queue = await loadQueueFromApi();
    expect(queue[0]?.materialBindings).toEqual([]);
  });
});
