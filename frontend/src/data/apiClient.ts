// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type {
  FleetData,
  MaterialActivity,
  MaterialPresence,
  MaterialUnitKind,
  PrinterViewModel,
  QueueEntryState,
  QueueViewModel,
} from '../domain';

interface ApiCapability {
  capabilityId: string;
  majorVersion: number;
}

interface ApiActiveJob {
  vendorJobId: string | null;
  name: string | null;
  state: PrinterViewModel['snapshot']['activeJob'] extends infer _ ?
    'queued' | 'transferring' | 'accepted' | 'preparing' | 'printing' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'unknown'
    : never;
  progress: number | null;
  elapsedSeconds: number | null;
  remainingSeconds: number | null;
  currentLayer: number | null;
  totalLayers: number | null;
}

interface ApiDetectedMaterial {
  materialFamily: string | null;
  vendorName: string | null;
  productName: string | null;
  rgbaHex: string | null;
  tag: { scheme: string; value: string } | null;
  remainingFraction: number | null;
}

interface ApiMaterialSystem {
  printerId: string;
  units: Array<{
    unitId: string;
    kind: MaterialUnitKind;
    label: string | null;
    position: number;
    slots: Array<{
      slotId: string;
      unitId: string;
      position: number;
      label: string | null;
      presence: MaterialPresence;
      activity: MaterialActivity;
      detectedMaterial: ApiDetectedMaterial | null;
    }>;
  }>;
  observedAt: string;
  stale: boolean;
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
    activeJob: ApiActiveJob | null;
    observedAt: string;
    stale: boolean;
    faultSummary: Array<{
      code: string;
      severity: PrinterViewModel['snapshot']['faultSummary'][number]['severity'];
      message: string | null;
    }>;
  };
  capabilities: ApiCapability[];
  materialSystem?: ApiMaterialSystem;
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
            vendorJobId: job.vendorJobId ?? undefined,
            name: job.name ?? undefined,
            state: job.state,
            progress: job.progress ?? undefined,
            elapsedSeconds: job.elapsedSeconds ?? undefined,
            remainingSeconds: job.remainingSeconds ?? undefined,
            currentLayer: job.currentLayer ?? undefined,
            totalLayers: job.totalLayers ?? undefined,
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
    materialSystem: printer.materialSystem ? mapMaterialSystem(printer.materialSystem) : undefined,
  };
}

function mapMaterialSystem(system: ApiMaterialSystem): NonNullable<PrinterViewModel['materialSystem']> {
  return {
    printerId: system.printerId,
    observedAt: system.observedAt,
    stale: system.stale,
    units: system.units.map((unit) => ({
      unitId: unit.unitId,
      kind: unit.kind,
      label: unit.label ?? undefined,
      position: unit.position,
      slots: unit.slots.map((slot) => ({
        slotId: slot.slotId,
        unitId: slot.unitId,
        position: slot.position,
        label: slot.label ?? undefined,
        presence: slot.presence,
        activity: slot.activity,
        detectedMaterial: slot.detectedMaterial
          ? {
              materialFamily: slot.detectedMaterial.materialFamily ?? undefined,
              vendorName: slot.detectedMaterial.vendorName ?? undefined,
              productName: slot.detectedMaterial.productName ?? undefined,
              rgbaHex: slot.detectedMaterial.rgbaHex ?? undefined,
              tag: slot.detectedMaterial.tag ?? undefined,
              remainingFraction: slot.detectedMaterial.remainingFraction ?? undefined,
            }
          : undefined,
      })),
    })),
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
