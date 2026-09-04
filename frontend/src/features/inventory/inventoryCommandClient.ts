// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { authenticatedCommandJson } from '../../data/commandClient';

export interface CreateSpoolPayload {
  spoolId: string;
  materialFamily: string;
  manufacturer?: string;
  productName?: string;
  rgbaHex?: string;
  initialFilamentMassG: string;
  emptySpoolMassG?: string;
  purchaseDate?: string;
}

export function newInventoryCommandId(prefix: string): string {
  return `inventory-${prefix}-${crypto.randomUUID()}`;
}

export async function createSpool(payload: CreateSpoolPayload, idempotencyKey: string): Promise<void> {
  await authenticatedCommandJson('/api/v1/inventory/spools', {
    method: 'POST',
    json: payload,
    idempotencyKey,
  });
}

export async function correctSpoolRemaining(
  spoolId: string,
  remainingFilamentMassG: string,
  note: string | undefined,
  idempotencyKey: string,
): Promise<void> {
  await authenticatedCommandJson(`/api/v1/inventory/spools/${encodeURIComponent(spoolId)}/correct-remaining`, {
    method: 'POST',
    json: { remainingFilamentMassG, ...(note ? { note } : {}) },
    idempotencyKey,
  });
}

export async function setEmptySpoolMass(
  spoolId: string,
  emptySpoolMassG: string | null,
  idempotencyKey: string,
): Promise<void> {
  await authenticatedCommandJson(`/api/v1/inventory/spools/${encodeURIComponent(spoolId)}/empty-spool-mass`, {
    method: 'PATCH',
    json: { emptySpoolMassG },
    idempotencyKey,
  });
}

export async function moveSpool(
  spoolId: string,
  printerId: string,
  slotId: string,
  idempotencyKey: string,
): Promise<void> {
  await authenticatedCommandJson(`/api/v1/inventory/spools/${encodeURIComponent(spoolId)}/assignment`, {
    method: 'PUT',
    json: { printerId, slotId },
    idempotencyKey,
  });
}

export async function unassignSpool(spoolId: string, idempotencyKey: string): Promise<void> {
  await authenticatedCommandJson(`/api/v1/inventory/spools/${encodeURIComponent(spoolId)}/assignment`, {
    method: 'DELETE',
    idempotencyKey,
  });
}

export async function archiveSpool(spoolId: string, idempotencyKey: string): Promise<void> {
  await authenticatedCommandJson(`/api/v1/inventory/spools/${encodeURIComponent(spoolId)}/archive`, {
    method: 'POST',
    idempotencyKey,
  });
}
