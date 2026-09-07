// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { TFunction } from 'i18next';

import type { PrinterViewModel } from '../../domain';

export function printerStatusTranslationKey(printer: PrinterViewModel): string {
  if (printer.snapshot.stale) return 'stale';
  if (printer.snapshot.connection !== 'connected') return printer.snapshot.connection;
  return printer.snapshot.operationalState;
}

export function relativeTimeLabel(observedAt: string, t: TFunction, nowMs: number = Date.now()): string {
  const observedMs = Date.parse(observedAt);
  if (Number.isNaN(observedMs)) return t('alpha.relative.recently');
  const deltaMs = Math.max(0, nowMs - observedMs);
  if (deltaMs < 60_000) return t('alpha.relative.justNow');
  if (deltaMs < 3_600_000) return t('alpha.relative.minutes', { count: Math.floor(deltaMs / 60_000) });
  if (deltaMs < 86_400_000) return t('alpha.relative.hours', { count: Math.floor(deltaMs / 3_600_000) });
  return t('alpha.relative.days', { count: Math.floor(deltaMs / 86_400_000) });
}
