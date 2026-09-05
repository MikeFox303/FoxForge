// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

const MAX_PRINTER_ID_LENGTH = 64;

export function normalizeBambuSerial(serialNumber: string): string {
  return serialNumber.trim().toUpperCase();
}

export function stableBambuPrinterId(serialNumber: string): string {
  const normalized = normalizeBambuSerial(serialNumber);
  if (!normalized) return '';

  const slug = normalized
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '');

  if (!slug) return '';
  return `bambu-${slug}`.slice(0, MAX_PRINTER_ID_LENGTH);
}
