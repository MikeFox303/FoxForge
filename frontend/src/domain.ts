// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'degraded';
export type OperationalState =
  | 'offline'
  | 'idle'
  | 'preparing'
  | 'printing'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelling'
  | 'unknown';
export type JobState =
  | 'queued'
  | 'transferring'
  | 'accepted'
  | 'preparing'
  | 'printing'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'unknown';
export type JobControlAction = 'pause' | 'resume' | 'cancel';
export type QueueEntryState =
  | 'pending'
  | 'blocked'
  | 'dispatching'
  | 'accepted'
  | 'preparing'
  | 'printing'
  | 'paused'
  | 'completed'
  | 'cancelled'
  | 'indeterminate'
  | 'failed';
export type FaultSeverity = 'info' | 'warning' | 'error' | 'critical';
export type MaterialUnitKind = 'multi_slot' | 'external' | 'toolhead' | 'other';
export type MaterialPresence = 'empty' | 'loaded' | 'unknown';
export type MaterialActivity = 'inactive' | 'active' | 'unknown';

export interface PrinterIdentity {
  printerId: string;
  displayName: string;
  vendor: string;
  model?: string;
  serialNumber?: string;
  adapterKind: string;
}

export interface ActiveJobSnapshot {
  vendorJobId?: string;
  name?: string;
  state: JobState;
  progress?: number;
  elapsedSeconds?: number;
  remainingSeconds?: number;
  currentLayer?: number;
  totalLayers?: number;
}

export interface PrinterFaultSummary {
  code: string;
  severity: FaultSeverity;
  message?: string;
}

export interface PrinterSnapshot {
  printerId: string;
  connection: ConnectionState;
  operationalState: OperationalState;
  activeJob?: ActiveJobSnapshot;
  observedAt: string;
  stale: boolean;
  faultSummary: PrinterFaultSummary[];
}

export interface CapabilityDescriptor {
  capabilityId: string;
  majorVersion: number;
  label: string;
  supportedActions?: JobControlAction[];
  requiresVendorJobIdentity?: boolean;
}

export interface DetectedMaterial {
  materialFamily?: string;
  vendorName?: string;
  productName?: string;
  rgbaHex?: string;
  tag?: { scheme: string; value: string };
  remainingFraction?: number;
}

export interface MaterialSlotSnapshot {
  slotId: string;
  unitId: string;
  position: number;
  label?: string;
  presence: MaterialPresence;
  activity: MaterialActivity;
  detectedMaterial?: DetectedMaterial;
}

export interface MaterialUnitSnapshot {
  unitId: string;
  kind: MaterialUnitKind;
  label?: string;
  position: number;
  slots: MaterialSlotSnapshot[];
}

export interface MaterialSystemSnapshot {
  printerId: string;
  units: MaterialUnitSnapshot[];
  observedAt: string;
  stale: boolean;
}

export interface PrinterViewModel {
  identity: PrinterIdentity;
  snapshot: PrinterSnapshot;
  capabilities: CapabilityDescriptor[];
  materialSystem?: MaterialSystemSnapshot;
}

export interface QueueViewModel {
  queueId: string;
  printerId: string;
  requestedName: string;
  filename: string;
  format: 'gcode' | '3mf';
  state: QueueEntryState;
  createdAt: string;
  updatedAt: string;
  attemptCount: number;
  blocker?: string;
  retryable?: boolean;
}

export interface FleetData {
  printers: PrinterViewModel[];
  queue: QueueViewModel[];
}
