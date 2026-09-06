// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { FleetData, MaterialSlotSnapshot, PrinterViewModel, QueueViewModel } from '../../domain';

export interface PrinterMaterialSummary {
  loadedSlots: number;
  activeSlots: number;
  lowSlots: number;
  totalSlots: number;
}

export type PrinterTelemetryPhase = 'live' | 'stale' | 'connecting' | 'degraded' | 'unavailable';
export type PrinterDetailTab = 'overview' | 'control' | 'materials' | 'queue' | 'diagnostics';

export function printerTelemetryPhase(printer: PrinterViewModel): PrinterTelemetryPhase {
  if (printer.snapshot.stale) return 'stale';
  if (printer.snapshot.connection === 'connecting') return 'connecting';
  if (printer.snapshot.connection === 'degraded') return 'degraded';
  if (printer.snapshot.connection !== 'connected' || printer.snapshot.operationalState === 'offline') return 'unavailable';
  return 'live';
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

export function hasJobControlCapability(printer: PrinterViewModel): boolean {
  return printer.capabilities.some((capability) => (
    capability.capabilityId === 'foxforge.job_control'
    && capability.majorVersion === 1
    && (capability.supportedActions?.length ?? 0) > 0
  ));
}

export function printerDetailTabs(printer: PrinterViewModel): PrinterDetailTab[] {
  const tabs: PrinterDetailTab[] = ['overview'];
  if (hasJobControlCapability(printer)) tabs.push('control');
  if (printer.materialSystem || printer.materialTopology) tabs.push('materials');
  tabs.push('queue', 'diagnostics');
  return tabs;
}

export function printerRoute(printerId: string): string {
  return `/printers/${encodeURIComponent(printerId)}`;
}
