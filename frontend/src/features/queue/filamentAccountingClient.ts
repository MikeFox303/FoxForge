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
  actualMassG?: string;
  state: FilamentReservationState;
  createdAt: string;
  updatedAt: string;
  note?: string;
}

export interface FilamentSpoolReservationView {
  spoolId: string;
  reservedMassG: string;
  availableMassG: string;
}

export interface FilamentAccountingSnapshot {
  apiVersion: '1';
  reservations: FilamentReservationView[];
  spools: FilamentSpoolReservationView[];
}

interface ApiReservation {
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

interface ApiAccountingSnapshot {
  apiVersion: '1';
  reservations: ApiReservation[];
  spools: FilamentSpoolReservationView[];
}

interface ApiQueueAccountingResult {
  apiVersion: '1';
  queueId: string;
  reservations: ApiReservation[];
  replayed: boolean;
}

export async function loadFilamentAccounting(): Promise<FilamentAccountingSnapshot> {
  const payload = await fetchJson<ApiAccountingSnapshot>('/api/v1/filament-accounting');
  return {
    apiVersion: payload.apiVersion,
    reservations: payload.reservations.map(mapReservation),
    spools: payload.spools,
  };
}

export async function planQueueFilament(
  queueId: string,
  estimates: ReadonlyArray<{ materialIndex: number; estimatedMassG: string }>,
  idempotencyKey: string,
): Promise<FilamentReservationView[]> {
  const result = await authenticatedCommandJson<ApiQueueAccountingResult>(
    `/api/v1/queue/${encodeURIComponent(queueId)}/filament-plan`,
    {
      method: 'POST',
      idempotencyKey,
      json: { estimates },
    },
  );
  return result.reservations.map(mapReservation);
}

export async function releaseQueueFilament(
  queueId: string,
  idempotencyKey: string,
): Promise<FilamentReservationView[]> {
  const result = await authenticatedCommandJson<ApiQueueAccountingResult>(
    `/api/v1/queue/${encodeURIComponent(queueId)}/filament-release`,
    {
      method: 'POST',
      idempotencyKey,
    },
  );
  return result.reservations.map(mapReservation);
}

export async function reconcileQueueFilament(
  queueId: string,
  materialIndex: number,
  actualMassG: string,
  note: string | undefined,
  idempotencyKey: string,
): Promise<FilamentReservationView[]> {
  const result = await authenticatedCommandJson<ApiQueueAccountingResult>(
    `/api/v1/queue/${encodeURIComponent(queueId)}/filament-reconcile`,
    {
      method: 'POST',
      idempotencyKey,
      json: {
        materialIndex,
        actualMassG,
        note: note?.trim() || null,
      },
    },
  );
  return result.reservations.map(mapReservation);
}

function mapReservation(item: ApiReservation): FilamentReservationView {
  return {
    queueId: item.queueId,
    materialIndex: item.materialIndex,
    spoolId: item.spoolId,
    printerId: item.printerId,
    slotId: item.slotId,
    estimatedMassG: item.estimatedMassG,
    actualMassG: item.actualMassG ?? undefined,
    state: item.state,
    createdAt: item.createdAt,
    updatedAt: item.updatedAt,
    note: item.note ?? undefined,
  };
}
