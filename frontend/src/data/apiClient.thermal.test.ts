// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { afterEach, describe, expect, it, vi } from 'vitest';

import { loadFleetFromApi } from './apiClient';

const fetchMock = vi.fn<typeof fetch>();

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe('thermal telemetry API mapping', () => {
  it('maps the common capability and zones without vendor-wire knowledge', async () => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      apiVersion: '1',
      printers: [{
        identity: {
          printerId: 'bambu-x2d-main',
          displayName: 'X2D',
          vendor: 'Bambu Lab',
          model: 'X2D',
          serialNumber: 'SERIAL',
          adapterKind: 'bambu',
        },
        snapshot: {
          printerId: 'bambu-x2d-main',
          connection: 'connected',
          operationalState: 'idle',
          activeJob: null,
          observedAt: '2026-09-07T18:00:00Z',
          stale: false,
          faultSummary: [],
        },
        capabilities: [{
          capabilityId: 'foxforge.thermal_telemetry',
          majorVersion: 1,
          reportsTargets: true,
        }],
        thermalTelemetry: {
          printerId: 'bambu-x2d-main',
          observedAt: '2026-09-07T18:00:00Z',
          stale: false,
          zones: [
            {
              zoneId: 'hotend:0',
              kind: 'hotend',
              position: 0,
              label: 'Right hotend',
              currentCelsius: 41,
              targetCelsius: 0,
            },
            {
              zoneId: 'bed:0',
              kind: 'bed',
              position: 10,
              label: 'Bed',
              currentCelsius: 35,
              targetCelsius: 0,
            },
          ],
        },
      }],
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    const data = await loadFleetFromApi();
    const printer = data.printers[0];

    expect(printer.capabilities[0]).toMatchObject({
      capabilityId: 'foxforge.thermal_telemetry',
      reportsTargets: true,
    });
    expect(printer.thermalTelemetry?.zones).toEqual([
      {
        zoneId: 'hotend:0',
        kind: 'hotend',
        position: 0,
        label: 'Right hotend',
        currentCelsius: 41,
        targetCelsius: 0,
      },
      {
        zoneId: 'bed:0',
        kind: 'bed',
        position: 10,
        label: 'Bed',
        currentCelsius: 35,
        targetCelsius: 0,
      },
    ]);
  });
});
