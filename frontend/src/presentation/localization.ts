// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { TFunction } from 'i18next';

import type {
  ConnectionState,
  MaterialPresence,
  MaterialUnitKind,
  OperationalState,
  PrinterViewModel,
  QueueEntryState,
} from '../domain';

export function localizedStatus(value: ConnectionState | OperationalState, t: TFunction): string {
  return t(`status.${value}`, { defaultValue: value.replaceAll('_', ' ') });
}

export function localizedPrinterStatus(printer: PrinterViewModel, t: TFunction): string {
  return localizedStatus(
    printer.snapshot.connection === 'connected' ? printer.snapshot.operationalState : printer.snapshot.connection,
    t,
  );
}

export function localizedQueueState(state: QueueEntryState, t: TFunction): string {
  return t(`queueState.${state}`, { defaultValue: state.replaceAll('_', ' ') });
}

export function localizedMaterialUnit(kind: MaterialUnitKind, t: TFunction): string {
  return t(`materialUnit.${kind}`, { defaultValue: t('materialUnit.other') });
}

export function localizedPresence(presence: MaterialPresence, t: TFunction): string {
  if (presence === 'loaded') return t('printerDetail.loaded');
  if (presence === 'empty') return t('common.empty');
  return t('status.unknown');
}

export function formatLocalizedRelativeTime(isoTimestamp: string, language: string, now = Date.now()): string {
  const timestamp = Date.parse(isoTimestamp);
  if (!Number.isFinite(timestamp)) return isoTimestamp;

  const deltaSeconds = Math.round((timestamp - now) / 1000);
  const absoluteSeconds = Math.abs(deltaSeconds);
  const formatter = new Intl.RelativeTimeFormat(language, { numeric: 'auto' });

  if (absoluteSeconds < 60) return formatter.format(deltaSeconds, 'second');

  const deltaMinutes = Math.round(deltaSeconds / 60);
  if (Math.abs(deltaMinutes) < 60) return formatter.format(deltaMinutes, 'minute');

  const deltaHours = Math.round(deltaMinutes / 60);
  if (Math.abs(deltaHours) < 24) return formatter.format(deltaHours, 'hour');

  const deltaDays = Math.round(deltaHours / 24);
  return formatter.format(deltaDays, 'day');
}
