// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQueryClient } from '@tanstack/react-query';
import type { TFunction } from 'i18next';
import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { PrinterViewModel, QueueMaterialBindingView, QueueViewModel } from '../../domain';
import { inventoryQueryKey, useInventoryData } from '../inventory/inventoryGateway';
import {
  bindingSourceLabel,
  bindingToolheadLabel,
  findAssignedSpool,
  isExactNonnegativeDecimal,
  isExactPositiveDecimal,
  mayCreateAccountingPlan,
  mayReleaseAccountingPlan,
  reservationsForQueue,
  resolveReservationSpools,
  spoolLabel,
} from './accountingPresentation';
import {
  planQueueFilament,
  reconcileQueueFilament,
  releaseQueueFilament,
  type FilamentReservationView,
} from './filamentAccountingClient';
import {
  filamentAccountingQueryKey,
  useFilamentAccounting,
} from './filamentAccountingGateway';

type CommandIdentity = { fingerprint: string; key: string };

export function QueueAccountingPanel({
  entry,
  printer,
}: {
  entry: QueueViewModel;
  printer: PrinterViewModel | undefined;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const accounting = useFilamentAccounting();
  const inventory = useInventoryData();
  const reservations = reservationsForQueue(accounting.data.reservations, entry.queueId);
  const [estimates, setEstimates] = useState<Record<number, string>>({});
  const [actualMass, setActualMass] = useState<Record<number, string>>({});
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const planIdentity = useRef<CommandIdentity | undefined>(undefined);
  const releaseIdentity = useRef<CommandIdentity | undefined>(undefined);
  const reconciliationIdentities = useRef<Record<number, CommandIdentity>>({});

  if (entry.materialBindings.length === 0 && reservations.length === 0) return null;

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: filamentAccountingQueryKey }),
      queryClient.invalidateQueries({ queryKey: inventoryQueryKey }),
      queryClient.invalidateQueries({ queryKey: ['queue'] }),
    ]);
  };

  const submitPlan = async () => {
    const payload = entry.materialBindings
      .map((binding) => ({
        materialIndex: binding.materialIndex,
        estimatedMassG: estimates[binding.materialIndex]?.trim() ?? '',
      }))
      .sort((left, right) => left.materialIndex - right.materialIndex);
    const fingerprint = JSON.stringify(payload);
    const idempotencyKey = commandKey(planIdentity, fingerprint);
    setBusy('plan');
    setError(null);
    try {
      await planQueueFilament(entry.queueId, payload, idempotencyKey);
      planIdentity.current = undefined;
      await refresh();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(null);
    }
  };

  const releasePlan = async () => {
    if (!window.confirm(t('filamentAccounting.confirmRelease'))) return;
    const idempotencyKey = commandKey(releaseIdentity, 'release');
    setBusy('release');
    setError(null);
    try {
      await releaseQueueFilament(entry.queueId, idempotencyKey);
      releaseIdentity.current = undefined;
      await refresh();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(null);
    }
  };

  const reconcileReservation = async (reservation: FilamentReservationView) => {
    const materialIndex = reservation.materialIndex;
    const mass = actualMass[materialIndex]?.trim() ?? '';
    const note = notes[materialIndex]?.trim() || undefined;
    const fingerprint = JSON.stringify({ materialIndex, actualMassG: mass, note: note ?? null });
    const existing = reconciliationIdentities.current[materialIndex];
    const identity = existing?.fingerprint === fingerprint
      ? existing
      : { fingerprint, key: crypto.randomUUID() };
    reconciliationIdentities.current[materialIndex] = identity;
    setBusy(`reconcile:${materialIndex}`);
    setError(null);
    try {
      await reconcileQueueFilament(entry.queueId, materialIndex, mass, note, identity.key);
      delete reconciliationIdentities.current[materialIndex];
      setActualMass((current) => ({ ...current, [materialIndex]: '' }));
      setNotes((current) => ({ ...current, [materialIndex]: '' }));
      await refresh();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(null);
    }
  };

  const canPlan = accounting.phase === 'ready'
    && inventory.phase === 'ready'
    && reservations.length === 0
    && mayCreateAccountingPlan(entry)
    && entry.materialBindings.every((binding) => (
      isExactPositiveDecimal(estimates[binding.materialIndex] ?? '')
      && findAssignedSpool(inventory.data.spools, entry.printerId, binding.slotId) !== undefined
    ));

  return (
    <section className="queue-accounting-panel" aria-label={t('filamentAccounting.title')}>
      <div className="queue-accounting-heading">
        <div>
          <strong>{t('filamentAccounting.title')}</strong>
          <span>{t('filamentAccounting.boundary')}</span>
        </div>
        {accounting.isRefreshing && <small>{t('filamentAccounting.refreshing')}</small>}
      </div>

      {accounting.phase === 'loading' && (
        <div className="queue-accounting-notice" role="status">{t('filamentAccounting.loading')}</div>
      )}
      {accounting.phase === 'error' && (
        <div className="queue-accounting-notice warning-text" role="alert">
          <span>{t('filamentAccounting.unavailable')}</span>
          <button className="text-button" type="button" onClick={accounting.retry}>
            {t('filamentAccounting.retry')}
          </button>
        </div>
      )}

      {accounting.phase === 'ready' && reservations.length === 0 && (
        <PlanEditor
          entry={entry}
          printer={printer}
          inventory={inventory}
          estimates={estimates}
          disabled={busy !== null}
          onEstimateChange={(materialIndex, value) => {
            setEstimates((current) => ({ ...current, [materialIndex]: value }));
            planIdentity.current = undefined;
          }}
        />
      )}

      {accounting.phase === 'ready' && reservations.length > 0 && (
        <div className="queue-accounting-reservations">
          {reservations.map((reservation) => {
            const binding = bindingFor(entry, reservation);
            const resolution = resolveReservationSpools(inventory.data.spools, reservation);
            const toolhead = bindingToolheadLabel(printer, binding);
            return (
              <article
                className="queue-accounting-reservation"
                key={`${reservation.queueId}:${reservation.materialIndex}`}
              >
                <div className="queue-accounting-reservation-head">
                  <strong>{t('filamentAccounting.material', { index: reservation.materialIndex + 1 })}</strong>
                  <span className={`queue-accounting-state state-${reservation.state}`}>
                    {t(`filamentAccounting.states.${reservation.state}`)}
                  </span>
                </div>
                <div className="queue-accounting-facts">
                  <AccountingFact label={t('filamentAccounting.source')} value={bindingSourceLabel(printer, binding)} />
                  {toolhead && <AccountingFact label={t('filamentAccounting.toolhead')} value={toolhead} />}
                  <AccountingFact
                    label={t('filamentAccounting.reservedSpool')}
                    value={spoolLabel(resolution.reservedSpool) ?? shortId(reservation.spoolId)}
                  />
                  <AccountingFact
                    label={t('filamentAccounting.estimate')}
                    value={t('filamentAccounting.grams', { mass: reservation.estimatedMassG })}
                  />
                  {reservation.actualMassG !== undefined && (
                    <AccountingFact
                      label={t('filamentAccounting.actualMass')}
                      value={t('filamentAccounting.grams', { mass: reservation.actualMassG })}
                    />
                  )}
                </div>

                {resolution.state !== 'matched' && (
                  <div className="queue-accounting-drift warning-text" role="alert">
                    <strong>{t('filamentAccounting.assignmentDrift')}</strong>
                    <span>{driftText(resolution, t, reservation.spoolId)}</span>
                  </div>
                )}

                {reservation.note && <small className="queue-accounting-note">{reservation.note}</small>}

                {reservation.state === 'reconciliation_required' && (
                  <div className="queue-accounting-reconcile">
                    <p>{t('filamentAccounting.reconciliationText')}</p>
                    <label className="queue-command-field">
                      <span>{t('filamentAccounting.actualMass')}</span>
                      <input
                        type="text"
                        inputMode="decimal"
                        placeholder="0.000"
                        value={actualMass[reservation.materialIndex] ?? ''}
                        disabled={busy !== null}
                        onChange={(event) => {
                          const value = event.currentTarget.value;
                          setActualMass((current) => ({ ...current, [reservation.materialIndex]: value }));
                          delete reconciliationIdentities.current[reservation.materialIndex];
                        }}
                      />
                      <small>{t('filamentAccounting.actualMassHint')}</small>
                    </label>
                    <label className="queue-command-field">
                      <span>{t('filamentAccounting.note')}</span>
                      <input
                        type="text"
                        maxLength={512}
                        value={notes[reservation.materialIndex] ?? ''}
                        disabled={busy !== null}
                        onChange={(event) => {
                          const value = event.currentTarget.value;
                          setNotes((current) => ({ ...current, [reservation.materialIndex]: value }));
                          delete reconciliationIdentities.current[reservation.materialIndex];
                        }}
                      />
                    </label>
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={busy !== null || !isExactNonnegativeDecimal(actualMass[reservation.materialIndex] ?? '')}
                      onClick={() => void reconcileReservation(reservation)}
                    >
                      {busy === `reconcile:${reservation.materialIndex}`
                        ? t('filamentAccounting.saving')
                        : t('filamentAccounting.reconcile')}
                    </button>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {accounting.phase === 'ready' && reservations.length === 0 && !mayCreateAccountingPlan(entry) && (
        <div className="queue-accounting-notice warning-text">
          {entry.materialBindings.length === 0
            ? t('filamentAccounting.noBindings')
            : t('filamentAccounting.planClosed')}
        </div>
      )}

      {accounting.phase === 'ready' && reservations.length === 0 && mayCreateAccountingPlan(entry) && (
        <button
          className="secondary-button queue-accounting-plan-button"
          type="button"
          disabled={!canPlan || busy !== null}
          onClick={() => void submitPlan()}
        >
          {busy === 'plan' ? t('filamentAccounting.reserving') : t('filamentAccounting.reserve')}
        </button>
      )}

      {accounting.phase === 'ready' && mayReleaseAccountingPlan(entry, reservations) && (
        <button
          className="text-button queue-accounting-release"
          type="button"
          disabled={busy !== null}
          onClick={() => void releasePlan()}
        >
          {busy === 'release' ? t('filamentAccounting.releasing') : t('filamentAccounting.release')}
        </button>
      )}

      {error && <div className="queue-accounting-notice warning-text" role="alert">{error}</div>}
    </section>
  );
}

function PlanEditor({
  entry,
  printer,
  inventory,
  estimates,
  disabled,
  onEstimateChange,
}: {
  entry: QueueViewModel;
  printer: PrinterViewModel | undefined;
  inventory: ReturnType<typeof useInventoryData>;
  estimates: Record<number, string>;
  disabled: boolean;
  onEstimateChange: (materialIndex: number, value: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="queue-accounting-plan">
      <p>{t('filamentAccounting.planText')}</p>
      {inventory.phase === 'loading' && (
        <div className="queue-accounting-notice" role="status">{t('filamentAccounting.inventoryLoading')}</div>
      )}
      {inventory.phase === 'error' && (
        <div className="queue-accounting-notice warning-text" role="alert">
          <span>{t('filamentAccounting.inventoryUnavailable')}</span>
          <button className="text-button" type="button" onClick={inventory.retry}>
            {t('filamentAccounting.retry')}
          </button>
        </div>
      )}
      <div className="queue-accounting-plan-rows">
        {[...entry.materialBindings]
          .sort((left, right) => left.materialIndex - right.materialIndex)
          .map((binding) => {
            const assigned = findAssignedSpool(inventory.data.spools, entry.printerId, binding.slotId);
            const toolhead = bindingToolheadLabel(printer, binding);
            return (
              <article className="queue-accounting-plan-row" key={binding.materialIndex}>
                <div className="queue-accounting-reservation-head">
                  <strong>{t('filamentAccounting.material', { index: binding.materialIndex + 1 })}</strong>
                  <span>{bindingSourceLabel(printer, binding)}</span>
                </div>
                <div className="queue-accounting-facts">
                  {toolhead && <AccountingFact label={t('filamentAccounting.toolhead')} value={toolhead} />}
                  <AccountingFact
                    label={t('filamentAccounting.assignedSpool')}
                    value={spoolLabel(assigned) ?? t('filamentAccounting.noAssignedSpool')}
                  />
                  {assigned && (
                    <AccountingFact
                      label={t('filamentAccounting.remaining')}
                      value={t('filamentAccounting.grams', { mass: assigned.remainingFilamentMassG })}
                    />
                  )}
                </div>
                {!assigned && inventory.phase === 'ready' && (
                  <div className="queue-accounting-drift warning-text" role="alert">
                    {t('filamentAccounting.assignmentRequired')}
                  </div>
                )}
                <label className="queue-command-field">
                  <span>{t('filamentAccounting.estimate')}</span>
                  <input
                    type="text"
                    inputMode="decimal"
                    placeholder="0.000"
                    value={estimates[binding.materialIndex] ?? ''}
                    disabled={disabled}
                    onChange={(event) => onEstimateChange(binding.materialIndex, event.currentTarget.value)}
                  />
                  <small>{t('filamentAccounting.estimateHint')}</small>
                </label>
              </article>
            );
          })}
      </div>
    </div>
  );
}

function AccountingFact({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function bindingFor(entry: QueueViewModel, reservation: FilamentReservationView): QueueMaterialBindingView {
  return entry.materialBindings.find((binding) => binding.materialIndex === reservation.materialIndex) ?? {
    materialIndex: reservation.materialIndex,
    slotId: reservation.slotId,
  };
}

function commandKey(ref: { current: CommandIdentity | undefined }, fingerprint: string): string {
  if (ref.current?.fingerprint === fingerprint) return ref.current.key;
  const next = { fingerprint, key: crypto.randomUUID() };
  ref.current = next;
  return next.key;
}

function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}…` : value;
}

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : String(cause);
}

function driftText(
  resolution: ReturnType<typeof resolveReservationSpools>,
  t: TFunction,
  spoolId: string,
): string {
  if (resolution.state === 'replaced') {
    return t('filamentAccounting.driftReplaced', {
      spool: spoolLabel(resolution.currentAssignedSpool) ?? shortId(resolution.currentAssignedSpool?.spoolId ?? ''),
    });
  }
  if (resolution.state === 'unassigned') return t('filamentAccounting.driftUnassigned');
  if (resolution.state === 'reserved_spool_missing') {
    return t('filamentAccounting.driftMissing', { spool: shortId(spoolId) });
  }
  return '';
}
