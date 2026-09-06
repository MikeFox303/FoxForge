// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import type { PrinterViewModel } from '../../domain';
import type { ArtifactPrintPlan } from './queueCommandClient';
import {
  artifactFormatFromFilename,
  loadedMaterialSources,
  materialCompatibility,
  printerAcceptsFormat,
  requiresExplicitMaterialRouting,
  routePreview,
  routingReviewReady,
} from './queueMaterialRouting';

const printer: PrinterViewModel = {
  identity: {
    printerId: 'printer-opaque',
    displayName: 'Generic dual-toolhead printer',
    vendor: 'Any Vendor',
    model: 'Not-X2D',
    adapterKind: 'opaque',
  },
  snapshot: {
    printerId: 'printer-opaque',
    connection: 'connected',
    operationalState: 'idle',
    observedAt: '2026-09-06T00:00:00Z',
    stale: false,
    faultSummary: [],
  },
  capabilities: [
    {
      capabilityId: 'foxforge.print_execution',
      majorVersion: 1,
      label: 'foxforge.print_execution',
      acceptedFormats: ['3mf'],
      supportsPlateSelection: true,
      supportsMaterialBindings: true,
    },
  ],
  materialSystem: {
    printerId: 'printer-opaque',
    observedAt: '2026-09-06T00:00:00Z',
    stale: false,
    units: [
      {
        unitId: 'unit-1',
        kind: 'multi_slot',
        label: 'Material unit',
        position: 0,
        slots: [
          {
            slotId: 'slot-petg',
            unitId: 'unit-1',
            position: 0,
            label: 'A1',
            presence: 'loaded',
            activity: 'inactive',
            detectedMaterial: { materialFamily: 'PETG', rgbaHex: 'FF0000FF' },
          },
          {
            slotId: 'slot-pla',
            unitId: 'unit-1',
            position: 1,
            label: 'A2',
            presence: 'loaded',
            activity: 'inactive',
            detectedMaterial: { materialFamily: 'PLA' },
          },
          {
            slotId: 'slot-empty',
            unitId: 'unit-1',
            position: 2,
            label: 'A3',
            presence: 'empty',
            activity: 'inactive',
          },
        ],
      },
    ],
  },
  materialTopology: {
    printerId: 'printer-opaque',
    observedAt: '2026-09-06T00:00:00Z',
    stale: false,
    toolheads: [
      { toolheadId: 'tool-right', label: 'Right', position: 0 },
      { toolheadId: 'tool-left', label: 'Left', position: 1 },
    ],
    routes: [
      { sourceSlotId: 'slot-petg', toolheadIds: ['tool-right'], kind: 'fixed' },
      { sourceSlotId: 'slot-pla', toolheadIds: ['tool-left'], kind: 'fixed' },
    ],
  },
};

const plan: ArtifactPrintPlan = {
  artifactId: 'a'.repeat(64),
  artifactSha256: 'a'.repeat(64),
  readyForRouting: true,
  plates: [
    {
      plateIndex: 1,
      readyForRouting: true,
      materialRequirements: [
        {
          materialIndex: 0,
          materialFamily: 'PETG',
          rgbaHex: 'FFFFFFFF',
          profileName: 'Generic PETG',
          expectedToolheadPosition: 0,
        },
      ],
    },
  ],
  issues: [],
};

describe('queue material routing helpers', () => {
  it('uses generic print-execution metadata rather than vendor or model strings', () => {
    expect(artifactFormatFromFilename('part.3MF')).toBe('3mf');
    expect(printerAcceptsFormat(printer, '3mf')).toBe(true);
    expect(printerAcceptsFormat(printer, 'gcode')).toBe(false);
    expect(requiresExplicitMaterialRouting(printer, '3mf')).toBe(true);
    expect(requiresExplicitMaterialRouting(printer, 'gcode')).toBe(false);
  });

  it('offers only physically loaded sources and never chooses one automatically', () => {
    expect(loadedMaterialSources(printer).map((source) => source.slot.slotId)).toEqual([
      'slot-petg',
      'slot-pla',
    ]);
  });

  it('previews material and toolhead compatibility without replacing server compilation', () => {
    const requirement = plan.plates[0].materialRequirements[0];
    const sources = loadedMaterialSources(printer);
    expect(materialCompatibility(requirement, sources[0].slot)).toBe('match');
    expect(materialCompatibility(requirement, sources[1].slot)).toBe('mismatch');
    expect(routePreview(printer, requirement, 'slot-petg')).toEqual({
      state: 'ready',
      toolheadLabels: ['Right'],
    });
    expect(routePreview(printer, requirement, 'slot-pla').state).toBe('incompatible');
  });

  it('requires an explicit complete compatible binding set before enqueue review is ready', () => {
    expect(routingReviewReady({ printer, plan, plateIndex: 1, bindings: [] })).toBe(false);
    expect(routingReviewReady({
      printer,
      plan,
      plateIndex: 1,
      bindings: [{ materialIndex: 0, slotId: 'slot-pla' }],
    })).toBe(false);
    expect(routingReviewReady({
      printer,
      plan,
      plateIndex: 1,
      bindings: [{ materialIndex: 0, slotId: 'slot-petg' }],
    })).toBe(true);
  });

  it('keeps a selected ready plate usable when another plate is blocked', () => {
    const mixedPlan: ArtifactPrintPlan = {
      ...plan,
      readyForRouting: false,
      plates: [
        plan.plates[0],
        {
          plateIndex: 2,
          readyForRouting: false,
          materialRequirements: [],
        },
      ],
      issues: [
        {
          code: 'material_requirements_unknown',
          severity: 'blocking',
          message: 'Plate 2 has no material selection',
          plateIndex: 2,
        },
      ],
    };

    expect(routingReviewReady({
      printer,
      plan: mixedPlan,
      plateIndex: 1,
      bindings: [{ materialIndex: 0, slotId: 'slot-petg' }],
    })).toBe(true);
  });

  it('blocks selected plate toolhead metadata warnings just like the server compiler', () => {
    const unsafePlan: ArtifactPrintPlan = {
      ...plan,
      issues: [
        {
          code: 'toolhead_metadata_invalid',
          severity: 'warning',
          message: 'Toolhead intent could not be parsed safely',
          plateIndex: 1,
        },
      ],
    };

    expect(routingReviewReady({
      printer,
      plan: unsafePlan,
      plateIndex: 1,
      bindings: [{ materialIndex: 0, slotId: 'slot-petg' }],
    })).toBe(false);
  });

  it('fails closed when live material or topology evidence is stale', () => {
    const stalePrinter: PrinterViewModel = {
      ...printer,
      materialTopology: { ...printer.materialTopology!, stale: true },
    };
    expect(routingReviewReady({
      printer: stalePrinter,
      plan,
      plateIndex: 1,
      bindings: [{ materialIndex: 0, slotId: 'slot-petg' }],
    })).toBe(false);
    expect(routePreview(stalePrinter, plan.plates[0].materialRequirements[0], 'slot-petg').state).toBe('stale');
  });
});
