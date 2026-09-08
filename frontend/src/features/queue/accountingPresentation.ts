// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type {
  PrinterViewModel,
  QueueMaterialBindingView,
  QueueViewModel,
} from '../../domain';
import type { SpoolInventoryView } from '../inventory/types';
import type { FilamentReservationView } from './filamentAccountingClient';

const DECIMAL_PATTERN = /^(?:0|[1-9]\d*)(?:\.\d+)?$/;
const ZERO_PATTERN = /^0(?:\.0+)?$/;

export type ReservationAssignmentState =
  | 'matched'
  | 'unassigned'
  | 'replaced'
  | 'reserved_spool_missing';

export interface ReservationSpoolResolution {
  reservedSpool?: SpoolInventoryView;
  currentAssignedSpool?: SpoolInventoryView;
  state: ReservationAssignmentState;
}

export function isExactNonnegativeDecimal(value: string): boolean {
  return DECIMAL_PATTERN.test(value.trim());
}

export function isExactPositiveDecimal(value: string): boolean {
  const normalized = value.trim();
  return DECIMAL_PATTERN.test(normalized) && !ZERO_PATTERN.test(normalized);
}

export function reservationsForQueue(
  reservations: readonly FilamentReservationView[],
  queueId: string,
): FilamentReservationView[] {
  return reservations
    .filter((reservation) => reservation.queueId === queueId)
    .sort((left, right) => left.materialIndex - right.materialIndex);
}

export function findAssignedSpool(
  spools: readonly SpoolInventoryView[],
  printerId: string,
  slotId: string,
): SpoolInventoryView | undefined {
  return spools.find(
    (spool) => !spool.archived
      && spool.assignment?.printerId === printerId
      && spool.assignment.slotId === slotId,
  );
}

export function resolveReservationSpools(
  spools: readonly SpoolInventoryView[],
  reservation: FilamentReservationView,
): ReservationSpoolResolution {
  const reservedSpool = spools.find((spool) => spool.spoolId === reservation.spoolId);
  const currentAssignedSpool = findAssignedSpool(spools, reservation.printerId, reservation.slotId);
  if (!reservedSpool) {
    return { currentAssignedSpool, state: 'reserved_spool_missing' };
  }
  if (!currentAssignedSpool) {
    return { reservedSpool, state: 'unassigned' };
  }
  if (currentAssignedSpool.spoolId !== reservation.spoolId) {
    return { reservedSpool, currentAssignedSpool, state: 'replaced' };
  }
  return { reservedSpool, currentAssignedSpool, state: 'matched' };
}

export function bindingSourceLabel(
  printer: PrinterViewModel | undefined,
  binding: QueueMaterialBindingView,
): string {
  const slot = printer?.materialSystem?.units
    .flatMap((unit) => unit.slots)
    .find((candidate) => candidate.slotId === binding.slotId);
  return slot?.label?.trim() || binding.slotId;
}

export function bindingToolheadLabel(
  printer: PrinterViewModel | undefined,
  binding: QueueMaterialBindingView,
): string | undefined {
  if (!binding.toolheadId) return undefined;
  const toolhead = printer?.materialTopology?.toolheads.find(
    (candidate) => candidate.toolheadId === binding.toolheadId,
  );
  return toolhead?.label?.trim() || binding.toolheadId;
}

export function spoolLabel(spool: SpoolInventoryView | undefined): string | undefined {
  if (!spool) return undefined;
  return [spool.manufacturer, spool.productName, spool.materialFamily]
    .filter((value, index, values) => Boolean(value) && values.indexOf(value) === index)
    .join(' · ');
}

export function mayCreateAccountingPlan(entry: QueueViewModel): boolean {
  return entry.materialBindings.length > 0
    && entry.attemptCount === 0
    && ['pending', 'blocked', 'failed'].includes(entry.state);
}

export function mayReleaseAccountingPlan(
  entry: QueueViewModel,
  reservations: readonly FilamentReservationView[],
): boolean {
  return entry.attemptCount === 0
    && ['pending', 'blocked', 'failed'].includes(entry.state)
    && reservations.some((reservation) => reservation.state === 'reserved');
}
