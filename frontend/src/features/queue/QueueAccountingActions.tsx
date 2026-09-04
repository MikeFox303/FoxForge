// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { QueueViewModel } from '../../domain';
import {
  reconcileQueueFilament,
  releaseQueueFilament,
  type FilamentReservationView,
} from './filamentAccountingClient';
import { useFilamentAccounting } from './filamentAccountingGateway';

export function QueueAccountingActions({ entry }: { entry: QueueViewModel }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const accounting = useFilamentAccounting();
  const reservations = accounting.reservations.filter((item) => item.queueId === entry.queueId);
  const [actual, setActual] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!reservations.length) return null;

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['inventory'] }),
      queryClient.invalidateQueries({ queryKey: ['queue'] }),
    ]);
  };

  const reconcile = async (reservation: FilamentReservationView) => {
    const mass = (actual[reservation.materialIndex] ?? '').trim();
    if (!nonnegativeDecimal(mass)) return;
    setBusy(true);
    setError(null);
    try {
      await reconcileQueueFilament(
        entry.queueId,
        reservation.materialIndex,
        mass,
        crypto.randomUUID(),
      );
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  const release = async () => {
    if (!window.confirm(t('filamentAccounting.confirmRelease'))) return;
    setBusy(true);
    setError(null);
    try {
      await releaseQueueFilament(entry.queueId, crypto.randomUUID());
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  const mayRelease = ['pending', 'blocked'].includes(entry.state)
    && reservations.some((item) => item.state === 'reserved');

  return (
    <div className="queue-accounting-actions">
      {reservations.map((reservation) => (
        <div className="queue-accounting-reservation" key={`${reservation.queueId}:${reservation.materialIndex}`}>
          <span>{reservationLabel(reservation, t)}</span>
          {reservation.state === 'reconciliation_required' && (
            <div className="queue-accounting-reconcile">
              <label>
                <span>{t('filamentAccounting.actualMass')}</span>
                <input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="0.001"
                  value={actual[reservation.materialIndex] ?? ''}
                  disabled={busy}
                  onChange={(event) => setActual((current) => ({
                    ...current,
                    [reservation.materialIndex]: event.currentTarget.value,
                  }))}
                />
              </label>
              <button
                className="text-button warning-text"
                type="button"
                disabled={busy || !nonnegativeDecimal(actual[reservation.materialIndex] ?? '')}
                onClick={() => void reconcile(reservation)}
              >
                {t('filamentAccounting.reconcile')}
              </button>
            </div>
          )}
        </div>
      ))}
      {mayRelease && (
        <button className="text-button" type="button" disabled={busy} onClick={() => void release()}>
          {t('filamentAccounting.release')}
        </button>
      )}
      {error && <small className="warning-text">{error}</small>}
    </div>
  );
}

function reservationLabel(
  reservation: FilamentReservationView,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  if (reservation.state === 'consumed') {
    return t('filamentAccounting.consumed', { mass: reservation.actualMassG ?? reservation.estimatedMassG });
  }
  if (reservation.state === 'released') return t('filamentAccounting.released');
  if (reservation.state === 'reconciliation_required') return t('filamentAccounting.reconciliationRequired');
  return t('filamentAccounting.reserved', { mass: reservation.estimatedMassG });
}

function nonnegativeDecimal(value: string): boolean {
  if (!value.trim()) return false;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0;
}
