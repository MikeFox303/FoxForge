// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { FleetData, MaterialSlotSnapshot, PrinterViewModel, QueueViewModel } from '../../domain';

export interface PrinterMaterialSummary {
  loadedSlots: number;
  activeSlots: number;
  lowSlots: number;
  totalSlots: number;
}

export function printerByRouteId(fleet: FleetData, routePrinterId?: string): PrinterViewModel | undefined {
  if (!routePrinterId) return undefined;
  const printerId = decodeURIComponent(routePrinterId);
  return fleet.printers.find((printer) => printer.identity.printerId === printerId);
}

export function queueForPrinter(fleet: FleetData, printerId: string): QueueViewModel[] {
  return fleet.queue.filter((entry) => entry.printerId === printerId);
}

export function materialSlots(printer: PrinterViewModel): MaterialSlotSnapshot[] {
  return printer.materialSystem?.units.flatMap((unit) => unit.slots) ?? [];
}

export function summarizePrinterMaterials(printer: PrinterViewModel): PrinterMaterialSummary {
  const slots = materialSlots(printer);
  return {
    loadedSlots: slots.filter((slot) => slot.presence === 'loaded').length,
    activeSlots: slots.filter((slot) => slot.activity === 'active').length,
    lowSlots: slots.filter((slot) => slot.presence === 'loaded' && (slot.detectedMaterial?.remainingFraction ?? 1) <= 0.2).length,
    totalSlots: slots.length,
  };
}

export function printerRoute(printerId: string): string {
  return `/printers/${encodeURIComponent(printerId)}`;
}
