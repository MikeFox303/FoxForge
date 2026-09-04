// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { fetchJson } from '../../data/apiClient';
import { authenticatedCommandJson } from '../../data/commandClient';

export type FilamentReservationState =
  | 'reserved'
  | 'consumed'
  | 'released'
  | 'reconciliation_required';

export interface FilamentReservationView {
  queueId: string;
  materialIndex: number;
  spoolId: string;
  printerId: string;
  slotId: string;
  estimatedMassG: string;
  actualMassG: string | null;
  state: FilamentReservationState;
  createdAt: string;
  updatedAt: string;
  note: string | null;
}

export interface FilamentAccountingSnapshot {
  apiVersion: '1';
  reservations: FilamentReservationView[];
  spools: Array<{
    spoolId: string;
    reservedMassG: string;
    availableMassG: string;
  }>;
}

interface QueueAccountingResult {
  apiVersion: '1';
  queueId: string;
  reservations: FilamentReservationView[];
  replayed: boolean;
}

export interface FilamentEstimateInput {
  materialIndex: number;
  estimatedMassG: string;
}

export async function loadFilamentAccounting(): Promise<FilamentAccountingSnapshot> {
  return fetchJson<FilamentAccountingSnapshot>('/api/v1/filament-accounting');
}

export async function planQueueFilament(
  queueId: string,
  estimates: FilamentEstimateInput[],
  idempotencyKey: string,
): Promise<QueueAccountingResult> {
  return authenticatedCommandJson<QueueAccountingResult>(
    `/api/v1/queue/${encodeURIComponent(queueId)}/filament-plan`,
    {
      method: 'POST',
      idempotencyKey,
      json: { estimates },
    },
  );
}

export async function releaseQueueFilament(
  queueId: string,
  idempotencyKey: string,
): Promise<QueueAccountingResult> {
  return authenticatedCommandJson<QueueAccountingResult>(
    `/api/v1/queue/${encodeURIComponent(queueId)}/filament-release`,
    {
      method: 'POST',
      idempotencyKey,
    },
  );
}

export async function reconcileQueueFilament(
  queueId: string,
  materialIndex: number,
  actualMassG: string,
  idempotencyKey: string,
  note?: string,
): Promise<QueueAccountingResult> {
  return authenticatedCommandJson<QueueAccountingResult>(
    `/api/v1/queue/${encodeURIComponent(queueId)}/filament-reconcile`,
    {
      method: 'POST',
      idempotencyKey,
      json: {
        materialIndex,
        actualMassG,
        note: note?.trim() || undefined,
      },
    },
  );
}
