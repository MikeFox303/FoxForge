// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { FleetData, PrinterViewModel } from './domain';

export interface FleetSummary {
  totalPrinters: number;
  connectedPrinters: number;
  printingPrinters: number;
  queuedJobs: number;
  materialAlerts: number;
}

export function summarizeFleet(data: FleetData): FleetSummary {
  let materialAlerts = 0;

  for (const printer of data.printers) {
    for (const unit of printer.materialSystem?.units ?? []) {
      for (const slot of unit.slots) {
        const remaining = slot.detectedMaterial?.remainingFraction;
        if (slot.presence === 'loaded' && remaining !== undefined && remaining <= 0.2) {
          materialAlerts += 1;
        }
      }
    }
  }

  return {
    totalPrinters: data.printers.length,
    connectedPrinters: data.printers.filter((printer) => printer.snapshot.connection === 'connected').length,
    printingPrinters: data.printers.filter((printer) => printer.snapshot.operationalState === 'printing').length,
    queuedJobs: data.queue.filter((entry) => entry.state === 'pending' || entry.state === 'blocked').length,
    materialAlerts,
  };
}

export function formatDuration(seconds?: number): string {
  if (seconds === undefined) return '—';
  if (seconds < 60) return `${seconds}s`;

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours === 0) return `${minutes}m`;
  return `${hours}h ${minutes}m`;
}

export function formatPercent(value?: number): string {
  if (value === undefined) return '—';
  return `${Math.round(value * 100)}%`;
}

export function formatRelativeTime(observedAt: string, nowMs: number = Date.now()): string {
  const observedMs = Date.parse(observedAt);
  if (Number.isNaN(observedMs)) return 'Updated recently';

  const deltaMs = Math.max(0, nowMs - observedMs);
  if (deltaMs < 60_000) return 'Updated just now';
  if (deltaMs < 3_600_000) return `Updated ${Math.floor(deltaMs / 60_000)}m ago`;
  if (deltaMs < 86_400_000) return `Updated ${Math.floor(deltaMs / 3_600_000)}h ago`;
  return `Updated ${Math.floor(deltaMs / 86_400_000)}d ago`;
}

export function describeMaterialSource(printer: PrinterViewModel): string {
  const slots = printer.materialSystem?.units.flatMap((unit) => unit.slots) ?? [];
  const active = slots.find((slot) => slot.activity === 'active' && slot.detectedMaterial);
  const loaded = slots.find((slot) => slot.presence === 'loaded' && slot.detectedMaterial);
  const material = (active ?? loaded)?.detectedMaterial;

  if (!material) return 'No material loaded';
  return [material.materialFamily, material.vendorName].filter(Boolean).join(' · ') || 'Material loaded';
}

export function printerStatusLabel(printer: PrinterViewModel): string {
  if (printer.snapshot.stale) return 'Stale';
  if (printer.snapshot.connection !== 'connected') return printer.snapshot.connection;
  return printer.snapshot.operationalState;
}

export function printerTone(printer: PrinterViewModel): 'neutral' | 'good' | 'warning' | 'danger' | 'active' {
  const { connection, operationalState, stale } = printer.snapshot;
  if (stale || connection === 'degraded') return 'warning';
  if (connection === 'disconnected' || operationalState === 'failed' || operationalState === 'offline') return 'danger';
  if (operationalState === 'printing' || operationalState === 'preparing') return 'active';
  if (connection === 'connected' && operationalState === 'idle') return 'good';
  return 'neutral';
}

export function findPrinter(data: FleetData, printerId: string): PrinterViewModel | undefined {
  return data.printers.find((printer) => printer.identity.printerId === printerId);
}
