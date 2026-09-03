// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type {
  ActiveJobSnapshot,
  FleetData,
  MaterialSystemSnapshot,
  PrinterViewModel,
  QueueEntryState,
  QueueViewModel,
} from '../domain';

interface ApiCapability {
  capabilityId: string;
  majorVersion: number;
}

interface ApiPrinter {
  identity: {
    printerId: string;
    displayName: string;
    vendor: string;
    model: string | null;
    serialNumber: string | null;
    adapterKind: string;
  };
  snapshot: {
    printerId: string;
    connection: PrinterViewModel['snapshot']['connection'];
    operationalState: PrinterViewModel['snapshot']['operationalState'];
    activeJob: (Omit<ActiveJobSnapshot, 'vendorJobId' | 'name'> & {
      vendorJobId: string | null;
      name: string | null;
    }) | null;
    observedAt: string;
    stale: boolean;
    faultSummary: Array<{
      code: string;
      severity: PrinterViewModel['snapshot']['faultSummary'][number]['severity'];
      message: string | null;
    }>;
  };
  capabilities: ApiCapability[];
  materialSystem?: MaterialSystemSnapshot;
}

interface ApiFleetResponse {
  apiVersion: '1';
  printers: ApiPrinter[];
}

interface ApiQueueEntry {
  queueId: string;
  printerId: string;
  state: QueueEntryState;
  createdAt: string;
  updatedAt: string;
  attemptCount: number;
  request: {
    requestedName: string | null;
    artifact: {
      filename: string;
      format: 'gcode' | '3mf';
    };
  };
  assessment: {
    blockers: Array<{ code: string; message: string | null }>;
  } | null;
  error: { message: string } | null;
}

interface ApiQueueResponse {
  apiVersion: '1';
  entries: ApiQueueEntry[];
}

export async function loadFleetFromApi(): Promise<FleetData> {
  const [fleet, queue] = await Promise.all([
    fetchJson<ApiFleetResponse>('/api/v1/fleet'),
    fetchJson<ApiQueueResponse>('/api/v1/queue'),
  ]);

  return {
    printers: fleet.printers.map(mapPrinter),
    queue: queue.entries.map(mapQueueEntry),
  };
}

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`FoxForge API request failed: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function demoModeEnabled(): boolean {
  return typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('demo') === '1';
}

function mapPrinter(printer: ApiPrinter): PrinterViewModel {
  const job = printer.snapshot.activeJob;
  return {
    identity: {
      printerId: printer.identity.printerId,
      displayName: printer.identity.displayName,
      vendor: printer.identity.vendor,
      model: printer.identity.model ?? undefined,
      serialNumber: printer.identity.serialNumber ?? undefined,
      adapterKind: printer.identity.adapterKind,
    },
    snapshot: {
      printerId: printer.snapshot.printerId,
      connection: printer.snapshot.connection,
      operationalState: printer.snapshot.operationalState,
      activeJob: job
        ? {
            ...job,
            vendorJobId: job.vendorJobId ?? undefined,
            name: job.name ?? undefined,
          }
        : undefined,
      observedAt: printer.snapshot.observedAt,
      stale: printer.snapshot.stale,
      faultSummary: printer.snapshot.faultSummary.map((fault) => ({
        code: fault.code,
        severity: fault.severity,
        message: fault.message ?? undefined,
      })),
    },
    capabilities: printer.capabilities.map((capability) => ({
      capabilityId: capability.capabilityId,
      majorVersion: capability.majorVersion,
      label: capability.capabilityId,
    })),
    materialSystem: printer.materialSystem,
  };
}

function mapQueueEntry(entry: ApiQueueEntry): QueueViewModel {
  const blocker = entry.assessment?.blockers[0];
  return {
    queueId: entry.queueId,
    printerId: entry.printerId,
    requestedName: entry.request.requestedName ?? entry.request.artifact.filename,
    filename: entry.request.artifact.filename,
    format: entry.request.artifact.format,
    state: entry.state,
    createdAt: entry.createdAt,
    updatedAt: entry.updatedAt,
    attemptCount: entry.attemptCount,
    blocker: blocker?.message ?? blocker?.code ?? entry.error?.message,
  };
}
