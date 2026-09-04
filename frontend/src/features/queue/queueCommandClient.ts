// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { QueueEntryState } from '../../domain';
import { authenticatedCommandJson } from '../../data/commandClient';

export interface StagedArtifact {
  artifactId: string;
  filename: string;
  format: 'gcode' | '3mf';
  sizeBytes: number;
  sha256: string;
  replayed: boolean;
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

export async function enqueuePrintJob(options: {
  identity: QueueJobIdentity;
  printerId: string;
  artifactId: string;
  requestedName?: string;
}): Promise<QueueCommandResult> {
  return authenticatedCommandJson<QueueCommandResult>('/api/v1/queue', {
    method: 'POST',
    idempotencyKey: options.identity.enqueueIdempotencyKey,
    json: {
      queueId: options.identity.queueId,
      dispatchId: options.identity.dispatchId,
      printerId: options.printerId,
      artifactId: options.artifactId,
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
