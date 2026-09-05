// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import type { FleetData } from '../../domain';
import { archiveSpool, newInventoryCommandId, unassignSpool } from './inventoryCommandClient';
import { InventoryOperatorDialog, type InventoryDialogAction } from './InventoryOperatorDialog';
import { inventoryQueryKey, useInventoryData } from './inventoryGateway';
import {
  assignmentLabel,
  formatMass,
  remainingFraction,
  spoolDisplayName,
  spoolTone,
  summarizeInventory,
} from './inventoryViewModel';
import type { SpoolInventoryView } from './types';

interface DialogState {
  action: InventoryDialogAction;
  spool?: SpoolInventoryView;
}

export function InventoryView({ fleet }: { fleet: FleetData }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const inventoryRuntime = useInventoryData();
  const inventory = inventoryRuntime.data;
  const [search, setSearch] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [busySpool, setBusySpool] = useState<string | null>(null);
  const retryKeys = useRef<Record<string, string>>({});
  const summary = useMemo(() => summarizeInventory(inventory), [inventory]);
  const normalizedSearch = search.trim().toLocaleLowerCase();
  const visibleSpools = inventory.spools.filter((spool) => {
    if (!showArchived && spool.archived) return false;
    if (!normalizedSearch) return true;
    return [spool.materialFamily, spool.manufacturer, spool.productName, assignmentLabel(spool, fleet)]
      .filter(Boolean)
      .join(' ')
      .toLocaleLowerCase()
      .includes(normalizedSearch);
  });

  const refreshInventory = () => {
    void queryClient.invalidateQueries({ queryKey: ['inventory'] });
  };

  const directCommand = async (kind: 'unassign' | 'archive', spool: SpoolInventoryView) => {
    if (busySpool) return;
    if (kind === 'unassign' && !window.confirm(t('inventoryOperator.confirmUnassign'))) return;
    if (kind === 'archive') {
      if (spool.assignment) {
        setCommandError(t('inventoryOperator.archiveAssigned'));
        return;
      }
      if (!window.confirm(t('inventoryOperator.confirmArchive'))) return;
    }

    const retryIdentity = `${kind}:${spool.spoolId}`;
    const key = retryKeys.current[retryIdentity] ?? newInventoryCommandId(kind);
    retryKeys.current[retryIdentity] = key;
    setBusySpool(spool.spoolId);
    setCommandError(null);
    try {
      if (kind === 'unassign') await unassignSpool(spool.spoolId, key);
      else await archiveSpool(spool.spoolId, key);
      delete retryKeys.current[retryIdentity];
      refreshInventory();
    } catch (cause) {
      setCommandError(cause instanceof Error ? cause.message : t('inventoryOperator.commandFailed'));
    } finally {
      setBusySpool(null);
    }
  };

  return (
    <div className="stack-lg inventory-page">
      <div className="page-intro inventory-intro">
        <div>
          <div className="eyebrow">{t('inventory.eyebrow')}</div>
          <h2>{t('inventory.title')}</h2>
          <p>{t('inventory.subtitle')}</p>
        </div>
        <button className="primary-button" type="button" onClick={() => setDialog({ action: 'create' })}>{t('inventory.addSpool')}</button>
      </div>

      {commandError && <section className="runtime-notice error" role="alert"><span className="status-dot danger" aria-hidden="true" /><div><strong>{t('inventoryOperator.commandFailed')}</strong><span>{commandError}</span></div></section>}

      {inventoryRuntime.phase === 'loading' && (
        <section className="runtime-notice loading" role="status" aria-live="polite">
          <span className="runtime-spinner" aria-hidden="true" />
          <div><strong>{t('inventory.loadingTitle')}</strong><span>{t('inventory.loadingText')}</span></div>
        </section>
      )}

      {inventoryRuntime.phase === 'error' && (
        <section className="runtime-notice error" role="alert">
          <span className="status-dot danger" aria-hidden="true" />
          <div><strong>{t('inventory.errorTitle')}</strong><span>{t('inventory.errorText')}</span></div>
          <button className="secondary-button" type="button" onClick={inventoryRuntime.retry}>{t('inventory.retry')}</button>
        </section>
      )}

      {inventoryRuntime.isRefreshing && (
        <div className="inventory-refreshing" role="status" aria-live="polite">
          <span className="runtime-spinner" aria-hidden="true" />
          <span>{t('inventory.refreshing')}</span>
        </div>
      )}

      {inventoryRuntime.phase === 'ready' && <><section className="metric-grid inventory-metrics" aria-label={t('inventory.summary')}>
        <InventoryMetric label={t('inventory.activeSpools')} value={String(summary.activeSpools)} detail={t('inventory.activeSpoolsDetail')} />
        <InventoryMetric label={t('inventory.assigned')} value={String(summary.assignedSpools)} detail={t('inventory.assignedDetail')} />
        <InventoryMetric label={t('inventory.low')} value={String(summary.lowSpools)} detail={t('inventory.lowDetail')} warning={summary.lowSpools > 0} />
        <InventoryMetric label={t('inventory.remaining')} value={formatMass(summary.remainingMassG)} detail={t('inventory.remainingDetail')} />
      </section>

      <section className="panel inventory-toolbar">
        <label className="inventory-search">
          <span>{t('inventory.search')}</span>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t('inventory.searchPlaceholder')} />
        </label>
        <label className="inventory-archive-toggle">
          <input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />
          <span>{t('inventory.showArchived')}</span>
        </label>
      </section>

      <div className="inventory-grid">
        {visibleSpools.map((spool) => (
          <SpoolCard
            key={spool.spoolId}
            spool={spool}
            fleet={fleet}
            busy={busySpool === spool.spoolId}
            onDialog={(action) => setDialog({ action, spool })}
            onUnassign={() => void directCommand('unassign', spool)}
            onArchive={() => void directCommand('archive', spool)}
          />
        ))}
      </div>

      {visibleSpools.length === 0 && <div className="panel empty-state">{inventory.spools.length === 0 ? t('inventory.noSpools') : t('inventory.noMatches')}</div>}
      </>}

      <section className="callout inventory-boundary-note">
        <strong>{t('inventory.boundaryTitle')}</strong>
        <span>{t('inventory.boundaryText')}</span>
      </section>

      {dialog && <InventoryOperatorDialog
        action={dialog.action}
        spool={dialog.spool}
        fleet={fleet}
        onClose={() => setDialog(null)}
        onSuccess={() => {
          setCommandError(null);
          refreshInventory();
        }}
      />}
    </div>
  );
}

function InventoryMetric({ label, value, detail, warning = false }: { label: string; value: string; detail: string; warning?: boolean }) {
  return <article className={`metric-card ${warning ? 'tone-warning' : ''}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function SpoolCard({ spool, fleet, busy, onDialog, onUnassign, onArchive }: {
  spool: SpoolInventoryView;
  fleet: FleetData;
  busy: boolean;
  onDialog: (action: InventoryDialogAction) => void;
  onUnassign: () => void;
  onArchive: () => void;
}) {
  const { t } = useTranslation();
  const fraction = remainingFraction(spool);
  const tone = spoolTone(spool);
  const color = normalizeColor(spool.rgbaHex);
  const location = assignmentLabel(spool, fleet);

  return (
    <article className={`spool-card spool-${tone}`}>
      <div className="spool-card-head">
        <div className="spool-identity"><span className="spool-swatch" style={{ background: color }} aria-hidden="true" /><div><div className="vendor-label">{spool.materialFamily}</div><h3>{spoolDisplayName(spool)}</h3><span>{location}</span></div></div>
        <span className={`queue-badge ${tone === 'low' ? 'state-blocked' : tone === 'archived' || tone === 'empty' ? 'state-failed' : 'state-accepted'}`}>{spool.archived ? t('inventory.archived') : tone === 'low' ? t('inventory.lowBadge') : tone === 'empty' ? t('inventory.empty') : t('inventory.available')}</span>
      </div>

      <div className="spool-mass-row"><div><span>{t('inventory.remaining')}</span><strong>{formatMass(spool.remainingFilamentMassG)}</strong></div><div><span>{t('inventory.used')}</span><strong>{formatMass(spool.usedFilamentMassG)}</strong></div><div><span>{t('inventory.initial')}</span><strong>{formatMass(spool.initialFilamentMassG)}</strong></div></div>

      <div className="spool-progress" aria-label={`${Math.round(fraction * 100)}% ${t('inventory.remaining').toLocaleLowerCase()}`}><div className="progress-track"><div className="progress-value" style={{ width: `${Math.round(fraction * 100)}%` }} /></div><span>{Math.round(fraction * 100)}%</span></div>

      <div className="spool-meta-grid"><div><span>{t('inventory.location')}</span><strong>{location}</strong></div><div><span>{t('inventory.emptySpool')}</span><strong>{spool.emptySpoolMassG ? formatMass(spool.emptySpoolMassG) : '—'}</strong></div><div><span>{t('inventory.purchase')}</span><strong>{spool.purchaseDate ?? '—'}</strong></div><div><span>ID</span><strong>{spool.spoolId.slice(0, 8)}</strong></div></div>

      <div className="spool-actions inventory-operator-actions">
        {!spool.archived && <button className="secondary-button" type="button" disabled={busy} onClick={() => onDialog('correct')}>{t('inventory.correct')}</button>}
        {!spool.archived && <button className="text-button" type="button" disabled={busy} onClick={() => onDialog('move')}>{spool.assignment ? t('inventory.move') : t('inventoryOperator.moveTitle')}</button>}
        {!spool.archived && <button className="text-button" type="button" disabled={busy} onClick={() => onDialog('emptyMass')}>{t('inventoryOperator.editEmptyMass')}</button>}
        {spool.assignment && !spool.archived && <button className="text-button" type="button" disabled={busy} onClick={onUnassign}>{t('inventoryOperator.unassign')}</button>}
        <button className="text-button" type="button" disabled={busy} onClick={() => onDialog('history')}>{t('inventoryOperator.history')}</button>
        {!spool.archived && <button className="danger-button" type="button" disabled={busy || Boolean(spool.assignment)} title={spool.assignment ? t('inventoryOperator.archiveAssigned') : undefined} onClick={onArchive}>{t('inventoryOperator.archive')}</button>}
      </div>
    </article>
  );
}

function normalizeColor(value?: string): string {
  if (!value) return '#64748b';
  if (/^#[0-9a-fA-F]{8}$/.test(value)) return value.slice(0, 7);
  return value;
}
