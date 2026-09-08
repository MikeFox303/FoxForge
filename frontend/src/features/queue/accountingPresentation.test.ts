// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import type { PrinterViewModel, QueueViewModel } from '../../domain';
import type { SpoolInventoryView } from '../inventory/types';
import type { FilamentReservationView } from './filamentAccountingClient';
import {
  bindingSourceLabel,
  bindingToolheadLabel,
  findAssignedSpool,
  isExactNonnegativeDecimal,
  isExactPositiveDecimal,
  mayCreateAccountingPlan,
  mayReleaseAccountingPlan,
  reservationsForQueue,
  resolveReservationSpools,
  spoolLabel,
} from './accountingPresentation';

const queueEntry = (overrides: Partial<QueueViewModel> = {}): QueueViewModel => ({
  queueId: 'queue-1',
  printerId: 'printer-1',
  requestedName: 'Part',
  filename: 'part.3mf',
  format: '3mf',
  state: 'pending',
  createdAt: '2026-09-08T00:00:00Z',
  updatedAt: '2026-09-08T00:00:00Z',
  attemptCount: 0,
  materialBindings: [{ materialIndex: 0, slotId: 'slot-0', toolheadId: 'tool-0' }],
  ...overrides,
});

const reservation = (state: FilamentReservationView['state']): FilamentReservationView => ({
  queueId: 'queue-1',
  materialIndex: 0,
  spoolId: 'spool-1',
  printerId: 'printer-1',
  slotId: 'slot-0',
  estimatedMassG: '20.50',
  state,
  createdAt: '2026-09-08T00:00:00Z',
  updatedAt: '2026-09-08T00:00:00Z',
});

const printer: PrinterViewModel = {
  identity: {
    printerId: 'printer-1',
    displayName: 'Printer',
    vendor: 'test',
    adapterKind: 'fake',
  },
  snapshot: {
    printerId: 'printer-1',
    connection: 'connected',
    operationalState: 'idle',
    observedAt: '2026-09-08T00:00:00Z',
    stale: false,
    faultSummary: [],
  },
  capabilities: [],
  materialSystem: {
    printerId: 'printer-1',
    observedAt: '2026-09-08T00:00:00Z',
    stale: false,
    units: [{
      unitId: 'unit-0',
      kind: 'multi_slot',
      position: 0,
      slots: [{
        slotId: 'slot-0',
        unitId: 'unit-0',
        position: 0,
        label: 'AMS A1',
        presence: 'loaded',
        activity: 'inactive',
      }],
    }],
  },
  materialTopology: {
    printerId: 'printer-1',
    observedAt: '2026-09-08T00:00:00Z',
    stale: false,
    toolheads: [{ toolheadId: 'tool-0', label: 'Left toolhead', position: 0 }],
    routes: [],
  },
};

const spool: SpoolInventoryView = {
  spoolId: 'spool-1',
  materialFamily: 'PETG',
  manufacturer: 'SUNLU',
  productName: 'PETG',
  initialFilamentMassG: '1000',
  remainingFilamentMassG: '800',
  usedFilamentMassG: '200',
  usedFraction: '0.2',
  archived: false,
  assignment: {
    printerId: 'printer-1',
    slotId: 'slot-0',
    assignedAt: '2026-09-08T00:00:00Z',
  },
};

describe('accounting presentation', () => {
  it('accepts plain exact decimal strings and rejects exponent/sign/locale syntax', () => {
    expect(isExactPositiveDecimal('25.50')).toBe(true);
    expect(isExactPositiveDecimal('0.001')).toBe(true);
    expect(isExactPositiveDecimal('0')).toBe(false);
    expect(isExactPositiveDecimal('0.000')).toBe(false);
    expect(isExactPositiveDecimal('1e3')).toBe(false);
    expect(isExactPositiveDecimal('-1')).toBe(false);
    expect(isExactPositiveDecimal('1,5')).toBe(false);

    expect(isExactNonnegativeDecimal('0')).toBe(true);
    expect(isExactNonnegativeDecimal('0.000')).toBe(true);
    expect(isExactNonnegativeDecimal('12.5')).toBe(true);
    expect(isExactNonnegativeDecimal('-0.1')).toBe(false);
  });

  it('resolves physical source and compiler-owned toolhead labels without vendor inference', () => {
    const binding = queueEntry().materialBindings[0]!;
    expect(bindingSourceLabel(printer, binding)).toBe('AMS A1');
    expect(bindingToolheadLabel(printer, binding)).toBe('Left toolhead');
    expect(bindingSourceLabel(undefined, binding)).toBe('slot-0');
    expect(bindingToolheadLabel(undefined, binding)).toBe('tool-0');
  });

  it('resolves the FoxForge spool from inventory assignment only', () => {
    expect(findAssignedSpool([spool], 'printer-1', 'slot-0')).toEqual(spool);
    expect(findAssignedSpool([spool], 'printer-2', 'slot-0')).toBeUndefined();
    expect(spoolLabel(spool)).toBe('SUNLU · PETG');
  });

  it('keeps the reserved spool identity visible when the physical slot assignment changes', () => {
    expect(resolveReservationSpools([spool], reservation('reserved')).state).toBe('matched');

    const replacement: SpoolInventoryView = {
      ...spool,
      spoolId: 'spool-2',
      manufacturer: 'Bambu Lab',
      productName: 'PLA Basic',
      materialFamily: 'PLA',
    };
    expect(resolveReservationSpools([{ ...spool, assignment: undefined }, replacement], reservation('reserved'))).toEqual({
      reservedSpool: { ...spool, assignment: undefined },
      currentAssignedSpool: replacement,
      state: 'replaced',
    });
    expect(resolveReservationSpools([{ ...spool, assignment: undefined }], reservation('reserved')).state).toBe('unassigned');
    expect(resolveReservationSpools([], reservation('reserved')).state).toBe('reserved_spool_missing');
  });

  it('allows plan/release only before any durable dispatch attempt', () => {
    expect(mayCreateAccountingPlan(queueEntry())).toBe(true);
    expect(mayCreateAccountingPlan(queueEntry({ attemptCount: 1 }))).toBe(false);
    expect(mayCreateAccountingPlan(queueEntry({ state: 'accepted' }))).toBe(false);
    expect(mayCreateAccountingPlan(queueEntry({ materialBindings: [] }))).toBe(false);

    expect(mayReleaseAccountingPlan(queueEntry(), [reservation('reserved')])).toBe(true);
    expect(mayReleaseAccountingPlan(queueEntry({ attemptCount: 1 }), [reservation('reserved')])).toBe(false);
    expect(mayReleaseAccountingPlan(queueEntry(), [reservation('released')])).toBe(false);
  });

  it('filters and sorts reservations by durable queue/material identity', () => {
    const second = { ...reservation('reserved'), materialIndex: 2 };
    const first = { ...reservation('reserved'), materialIndex: 1 };
    const other = { ...reservation('reserved'), queueId: 'queue-2' };
    expect(reservationsForQueue([second, other, first], 'queue-1').map((item) => item.materialIndex)).toEqual([1, 2]);
  });
});
