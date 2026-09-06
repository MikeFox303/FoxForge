// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { PrintArtifactFormat, QueueEntryState } from '../../domain';
import { authenticatedCommandJson } from '../../data/commandClient';

export interface StagedArtifact {
  artifactId: string;
  filename: string;
  format: PrintArtifactFormat;
  sizeBytes: number;
  sha256: string;
  replayed: boolean;
}

export interface PrintPlanMaterialRequirement {
  materialIndex: number;
  materialFamily: string | null;
  rgbaHex: string | null;
  profileName: string | null;
  expectedToolheadPosition: number | null;
}

export interface PrintPlanPlate {
  plateIndex: number;
  readyForRouting: boolean;
  materialRequirements: PrintPlanMaterialRequirement[];
}

export interface PrintPlanIssue {
  code: string;
  severity: string;
  message: string;
  plateIndex: number | null;
}

export interface ArtifactPrintPlan {
  artifactId: string;
  artifactSha256: string;
  readyForRouting: boolean;
  plates: PrintPlanPlate[];
  issues: PrintPlanIssue[];
}

export interface MaterialBindingIntent {
  materialIndex: number;
  slotId: string;
}

export interface QueueCommandResult {
  queueId: string;
  printerId: string;
  state: QueueEntryState;
  replayed?: boolean;
  reconciliationRequired?: boolean;
  error?: {
    code: string;
    message: string;
    retryable: boolean;
    vendorCode?: string | null;
  } | null;
}

export interface QueueJobIdentity {
  queueId: string;
  dispatchId: string;
  enqueueIdempotencyKey: string;
}

export function createQueueJobIdentity(): QueueJobIdentity {
  return {
    queueId: crypto.randomUUID(),
    dispatchId: crypto.randomUUID(),
    enqueueIdempotencyKey: crypto.randomUUID(),
  };
}

export async function sha256File(file: Blob): Promise<string> {
  const bytes = await file.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

export async function stagePrintArtifact(file: File, sha256: string): Promise<StagedArtifact> {
  return authenticatedCommandJson<StagedArtifact>('/api/v1/artifacts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/octet-stream',
      'X-FoxForge-Filename': encodeURIComponent(file.name),
      'X-FoxForge-Sha256': sha256,
    },
    body: file,
  });
}

export async function inspectArtifactPrintPlan(artifactId: string): Promise<ArtifactPrintPlan> {
  return authenticatedCommandJson<ArtifactPrintPlan>(
    `/api/v1/artifacts/${encodeURIComponent(artifactId)}/print-plan`,
  );
}

export async function enqueuePrintJob(options: {
  identity: QueueJobIdentity;
  printerId: string;
  artifactId: string;
  requestedName?: string;
  plateIndex?: number;
  materialBindings?: MaterialBindingIntent[];
}): Promise<QueueCommandResult> {
  return authenticatedCommandJson<QueueCommandResult>('/api/v1/queue', {
    method: 'POST',
    idempotencyKey: options.identity.enqueueIdempotencyKey,
    json: {
      queueId: options.identity.queueId,
      dispatchId: options.identity.dispatchId,
      printerId: options.printerId,
      artifactId: options.artifactId,
      selection: options.plateIndex === undefined ? undefined : { plateIndex: options.plateIndex },
      materialBindings: options.materialBindings?.map((binding) => ({
        materialIndex: binding.materialIndex,
        slotId: binding.slotId,
      })),
      requestedName: options.requestedName || undefined,
    },
  });
}

export async function dispatchPrintJob(
  queueId: string,
  idempotencyKey: string,
): Promise<QueueCommandResult> {
  return authenticatedCommandJson<QueueCommandResult>(
    `/api/v1/queue/${encodeURIComponent(queueId)}/dispatch`,
    { method: 'POST', idempotencyKey },
  );
}

export async function reconcilePrintJob(
  queueId: string,
  accepted: boolean,
  idempotencyKey: string,
): Promise<QueueCommandResult> {
  return authenticatedCommandJson<QueueCommandResult>(
    `/api/v1/queue/${encodeURIComponent(queueId)}/reconcile`,
    {
      method: 'POST',
      idempotencyKey,
      json: { accepted },
    },
  );
}
