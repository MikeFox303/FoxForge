// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { ensureOperatorSession } from '../../data/printerSetupClient';

export interface AddSpoolPayload {
  materialFamily: string;
  manufacturer?: string;
  productName?: string;
  rgbaHex?: string;
  initialFilamentMassG: string;
  emptySpoolMassG?: string;
  purchaseDate?: string;
}

export async function addInventorySpool(payload: AddSpoolPayload): Promise<void> {
  await commandJson('/api/v1/inventory/spools', {
    method: 'POST',
    json: { spoolId: crypto.randomUUID(), ...payload },
  });
}

export async function correctSpoolRemaining(
  spoolId: string,
  remainingFilamentMassG: string,
  note?: string,
): Promise<void> {
  await commandJson(`/api/v1/inventory/spools/${encodeURIComponent(spoolId)}/correct-remaining`, {
    method: 'POST',
    json: { remainingFilamentMassG, note: note?.trim() || undefined },
  });
}

export async function setEmptySpoolMass(spoolId: string, emptySpoolMassG?: string): Promise<void> {
  await commandJson(`/api/v1/inventory/spools/${encodeURIComponent(spoolId)}/empty-spool-mass`, {
    method: 'PATCH',
    json: { emptySpoolMassG: emptySpoolMassG?.trim() || null },
  });
}

export async function moveInventorySpool(spoolId: string, printerId: string, slotId: string): Promise<void> {
  await commandJson(`/api/v1/inventory/spools/${encodeURIComponent(spoolId)}/assignment`, {
    method: 'PUT',
    json: { printerId, slotId },
  });
}

export async function unassignInventorySpool(spoolId: string): Promise<void> {
  await commandJson(`/api/v1/inventory/spools/${encodeURIComponent(spoolId)}/assignment`, {
    method: 'DELETE',
  });
}

export async function archiveInventorySpool(spoolId: string): Promise<void> {
  await commandJson(`/api/v1/inventory/spools/${encodeURIComponent(spoolId)}/archive`, {
    method: 'POST',
  });
}

async function commandJson(
  path: string,
  options: { method: string; json?: object },
): Promise<unknown> {
  const token = await ensureOperatorSession();
  const headers = new Headers({
    Authorization: `Bearer ${token}`,
    'Idempotency-Key': crypto.randomUUID(),
  });
  if (options.json) headers.set('Content-Type', 'application/json');

  const response = await fetch(path, {
    method: options.method,
    headers,
    body: options.json ? JSON.stringify(options.json) : undefined,
  });
  const payload = await response.json().catch(() => null) as unknown;
  if (!response.ok) throw apiError(response.status, payload);
  return payload;
}

function apiError(status: number, payload: unknown): Error {
  if (isRecord(payload) && isRecord(payload.error) && typeof payload.error.message === 'string') {
    return new Error(payload.error.message);
  }
  return new Error(`FoxForge inventory command failed (${status}).`);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
