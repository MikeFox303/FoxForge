// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { FleetData } from './domain';

const observedAt = '2026-09-04T00:58:00Z';

export const fleetData: FleetData = {
  printers: [
    {
      identity: {
        printerId: 'bambu-x2d-main',
        displayName: 'X2D Main',
        vendor: 'Bambu Lab',
        model: 'X2D',
        adapterKind: 'bambu',
      },
      snapshot: {
        printerId: 'bambu-x2d-main',
        connection: 'connected',
        operationalState: 'printing',
        observedAt,
        stale: false,
        faultSummary: [],
        activeJob: {
          vendorJobId: 'bambu-job-2147',
          name: 'camera_mount_v7.3mf',
          state: 'printing',
          progress: 0.64,
          elapsedSeconds: 5040,
          remainingSeconds: 2760,
          currentLayer: 282,
          totalLayers: 441,
        },
      },
      capabilities: [
        { capabilityId: 'foxforge.print_execution', majorVersion: 1, label: 'Print execution' },
        { capabilityId: 'foxforge.material_system', majorVersion: 1, label: 'Material system' },
      ],
      materialSystem: {
        printerId: 'bambu-x2d-main',
        observedAt,
        stale: false,
        units: [
          {
            unitId: 'ams-2-pro-1',
            kind: 'multi_slot',
            label: 'AMS 2 Pro',
            position: 0,
            slots: [
              {
                slotId: 'ams-1-a1',
                unitId: 'ams-2-pro-1',
                position: 0,
                label: 'A1',
                presence: 'loaded',
                activity: 'active',
                detectedMaterial: {
                  materialFamily: 'PETG',
                  vendorName: 'SUNLU',
                  productName: 'PETG Black',
                  rgbaHex: '#202124ff',
                  remainingFraction: 0.61,
                },
              },
              {
                slotId: 'ams-1-a2',
                unitId: 'ams-2-pro-1',
                position: 1,
                label: 'A2',
                presence: 'loaded',
                activity: 'inactive',
                detectedMaterial: {
                  materialFamily: 'PLA',
                  vendorName: 'SUNLU',
                  productName: 'PLA White',
                  rgbaHex: '#f3f4f6ff',
                  remainingFraction: 0.34,
                },
              },
              {
                slotId: 'ams-1-a3',
                unitId: 'ams-2-pro-1',
                position: 2,
                label: 'A3',
                presence: 'loaded',
                activity: 'inactive',
                detectedMaterial: {
                  materialFamily: 'PETG',
                  vendorName: 'SUNLU',
                  productName: 'PETG Orange',
                  rgbaHex: '#f97316ff',
                  remainingFraction: 0.18,
                },
              },
              {
                slotId: 'ams-1-a4',
                unitId: 'ams-2-pro-1',
                position: 3,
                label: 'A4',
                presence: 'empty',
                activity: 'inactive',
              },
            ],
          },
        ],
      },
    },
    {
      identity: {
        printerId: 'ender3-v3-ke',
        displayName: 'Ender KE',
        vendor: 'Creality',
        model: 'Ender-3 V3 KE',
        adapterKind: 'moonraker',
      },
      snapshot: {
        printerId: 'ender3-v3-ke',
        connection: 'connected',
        operationalState: 'idle',
        observedAt,
        stale: false,
        faultSummary: [],
      },
      capabilities: [
        { capabilityId: 'foxforge.print_execution', majorVersion: 1, label: 'Print execution' },
        { capabilityId: 'foxforge.material_system', majorVersion: 1, label: 'Material system' },
      ],
      materialSystem: {
        printerId: 'ender3-v3-ke',
        observedAt,
        stale: false,
        units: [
          {
            unitId: 'external-spool',
            kind: 'external',
            label: 'External spool',
            position: 0,
            slots: [
              {
                slotId: 'external-0',
                unitId: 'external-spool',
                position: 0,
                label: 'Spool',
                presence: 'loaded',
                activity: 'inactive',
                detectedMaterial: {
                  materialFamily: 'PETG',
                  vendorName: 'SUNLU',
                  productName: 'PETG Grey',
                  rgbaHex: '#6b7280ff',
                  remainingFraction: 0.72,
                },
              },
            ],
          },
        ],
      },
    },
  ],
  queue: [
    {
      queueId: '6c39b456-75e0-47f4-a91d-9ec6a9a5e501',
      printerId: 'bambu-x2d-main',
      requestedName: 'Camera mount v7',
      filename: 'camera_mount_v7.3mf',
      format: '3mf',
      state: 'accepted',
      createdAt: '2026-09-04T00:23:00Z',
      updatedAt: '2026-09-04T00:25:00Z',
      attemptCount: 1,
    },
    {
      queueId: '4e1789fa-b7b7-4e4f-9a67-b2046ac1c341',
      printerId: 'ender3-v3-ke',
      requestedName: 'Cable clip batch',
      filename: 'cable_clips.gcode',
      format: 'gcode',
      state: 'pending',
      createdAt: '2026-09-04T00:51:00Z',
      updatedAt: '2026-09-04T00:51:00Z',
      attemptCount: 0,
    },
    {
      queueId: '2883e980-0e6f-43a3-a5bf-90ec50b0683f',
      printerId: 'bambu-x2d-main',
      requestedName: 'Drone arm guard',
      filename: 'drone_arm_guard.3mf',
      format: '3mf',
      state: 'blocked',
      createdAt: '2026-09-04T00:54:00Z',
      updatedAt: '2026-09-04T00:54:00Z',
      attemptCount: 0,
      blocker: 'Printer is busy with an active job',
    },
  ],
};
