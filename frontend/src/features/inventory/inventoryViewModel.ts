// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { FleetData } from '../../domain';
import type { InventoryData, SpoolInventoryView } from './types';

export interface InventorySummary {
  activeSpools: number;
  assignedSpools: number;
  lowSpools: number;
  remainingMassG: number;
}

export function decimalNumber(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function remainingFraction(spool: SpoolInventoryView): number {
  const initial = decimalNumber(spool.initialFilamentMassG);
  if (initial <= 0) return 0;
  return Math.max(0, Math.min(1, decimalNumber(spool.remainingFilamentMassG) / initial));
}

export function summarizeInventory(data: InventoryData): InventorySummary {
  const active = data.spools.filter((spool) => !spool.archived);
  return {
    activeSpools: active.length,
    assignedSpools: active.filter((spool) => spool.assignment).length,
    lowSpools: active.filter((spool) => remainingFraction(spool) <= 0.2).length,
    remainingMassG: active.reduce((total, spool) => total + decimalNumber(spool.remainingFilamentMassG), 0),
  };
}

export function formatMass(value: string | number): string {
  const grams = typeof value === 'number' ? value : decimalNumber(value);
  if (grams >= 1000) return `${(grams / 1000).toFixed(2).replace(/\.00$/, '')} kg`;
  return `${Math.round(grams)} g`;
}

export function spoolDisplayName(spool: SpoolInventoryView): string {
  return [spool.manufacturer, spool.productName].filter(Boolean).join(' ') || spool.materialFamily;
}

export function assignmentLabel(spool: SpoolInventoryView, fleet: FleetData): string {
  if (!spool.assignment) return 'Storage';
  const printer = fleet.printers.find((candidate) => candidate.identity.printerId === spool.assignment?.printerId);
  if (!printer) return 'Assigned to printer';

  const slot = printer.materialSystem?.units.flatMap((unit) => unit.slots).find((candidate) => candidate.slotId === spool.assignment?.slotId);
  return slot?.label ? `${printer.identity.displayName} · ${slot.label}` : printer.identity.displayName;
}

export function spoolTone(spool: SpoolInventoryView): 'normal' | 'low' | 'empty' | 'archived' {
  if (spool.archived) return 'archived';
  const fraction = remainingFraction(spool);
  if (fraction <= 0) return 'empty';
  if (fraction <= 0.2) return 'low';
  return 'normal';
}
