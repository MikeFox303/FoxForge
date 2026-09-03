// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { FleetData } from '../../domain';
import { useInventoryData } from './inventoryGateway';
import {
  assignmentLabel,
  formatMass,
  remainingFraction,
  spoolDisplayName,
  spoolTone,
  summarizeInventory,
} from './inventoryViewModel';
import type { SpoolInventoryView } from './types';

export function InventoryView({ fleet }: { fleet: FleetData }) {
  const { t } = useTranslation();
  const inventory = useInventoryData();
  const [search, setSearch] = useState('');
  const [showArchived, setShowArchived] = useState(false);
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

  return (
    <div className="stack-lg inventory-page">
      <div className="page-intro inventory-intro">
        <div>
          <div className="eyebrow">{t('inventory.eyebrow')}</div>
          <h2>{t('inventory.title')}</h2>
          <p>{t('inventory.subtitle')}</p>
        </div>
        <button className="primary-button" disabled title={t('inventory.requiresApi')}>{t('inventory.addSpool')}</button>
      </div>

      <section className="metric-grid inventory-metrics" aria-label={t('inventory.summary')}>
        <InventoryMetric label={t('inventory.activeSpools')} value={String(summary.activeSpools)} detail={t('inventory.activeSpoolsDetail')} />
        <InventoryMetric label={t('inventory.assigned')} value={String(summary.assignedSpools)} detail={t('inventory.assignedDetail')} />
        <InventoryMetric label={t('inventory.low')} value={String(summary.lowSpools)} detail={t('inventory.lowDetail')} warning={summary.lowSpools > 0} />
        <InventoryMetric label={t('inventory.remaining')} value={formatMass(summary.remainingMassG)} detail={t('inventory.remainingDetail')} />
      </section>

      <section className="panel inventory-toolbar">
        <label className="inventory-search">
          <span>{t('inventory.search')}</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t('inventory.searchPlaceholder')}
          />
        </label>
        <label className="inventory-archive-toggle">
          <input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />
          <span>{t('inventory.showArchived')}</span>
        </label>
      </section>

      <div className="inventory-grid">
        {visibleSpools.map((spool) => (
          <SpoolCard key={spool.spoolId} spool={spool} fleet={fleet} />
        ))}
      </div>

      {visibleSpools.length === 0 && <div className="panel empty-state">{t('inventory.noMatches')}</div>}

      <section className="callout inventory-boundary-note">
        <strong>{t('inventory.boundaryTitle')}</strong>
        <span>{t('inventory.boundaryText')}</span>
      </section>
    </div>
  );
}

function InventoryMetric({
  label,
  value,
  detail,
  warning = false,
}: {
  label: string;
  value: string;
  detail: string;
  warning?: boolean;
}) {
  return (
    <article className={`metric-card ${warning ? 'tone-warning' : ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function SpoolCard({ spool, fleet }: { spool: SpoolInventoryView; fleet: FleetData }) {
  const { t } = useTranslation();
  const fraction = remainingFraction(spool);
  const tone = spoolTone(spool);
  const color = normalizeColor(spool.rgbaHex);
  const location = assignmentLabel(spool, fleet);

  return (
    <article className={`spool-card spool-${tone}`}>
      <div className="spool-card-head">
        <div className="spool-identity">
          <span className="spool-swatch" style={{ background: color }} aria-hidden="true" />
          <div>
            <div className="vendor-label">{spool.materialFamily}</div>
            <h3>{spoolDisplayName(spool)}</h3>
            <span>{location}</span>
          </div>
        </div>
        <span className={`queue-badge ${tone === 'low' ? 'state-blocked' : tone === 'archived' ? 'state-failed' : tone === 'empty' ? 'state-failed' : 'state-accepted'}`}>
          {spool.archived ? t('inventory.archived') : tone === 'low' ? t('inventory.lowBadge') : tone === 'empty' ? t('inventory.empty') : t('inventory.available')}
        </span>
      </div>

      <div className="spool-mass-row">
        <div>
          <span>{t('inventory.remaining')}</span>
          <strong>{formatMass(spool.remainingFilamentMassG)}</strong>
        </div>
        <div>
          <span>{t('inventory.used')}</span>
          <strong>{formatMass(spool.usedFilamentMassG)}</strong>
        </div>
        <div>
          <span>{t('inventory.initial')}</span>
          <strong>{formatMass(spool.initialFilamentMassG)}</strong>
        </div>
      </div>

      <div className="spool-progress" aria-label={`${Math.round(fraction * 100)}% ${t('inventory.remaining').toLocaleLowerCase()}`}>
        <div className="progress-track">
          <div className="progress-value" style={{ width: `${Math.round(fraction * 100)}%` }} />
        </div>
        <span>{Math.round(fraction * 100)}%</span>
      </div>

      <div className="spool-meta-grid">
        <div><span>{t('inventory.location')}</span><strong>{location}</strong></div>
        <div><span>{t('inventory.emptySpool')}</span><strong>{spool.emptySpoolMassG ? formatMass(spool.emptySpoolMassG) : '—'}</strong></div>
        <div><span>{t('inventory.purchase')}</span><strong>{spool.purchaseDate ?? '—'}</strong></div>
        <div><span>ID</span><strong>{spool.spoolId.slice(0, 8)}</strong></div>
      </div>

      <div className="spool-actions">
        <button className="secondary-button" disabled title={t('inventory.requiresApi')}>{t('inventory.correct')}</button>
        <button className="text-button" disabled title={t('inventory.requiresApi')}>{t('inventory.move')}</button>
      </div>
    </article>
  );
}

function normalizeColor(value?: string): string {
  if (!value) return '#64748b';
  if (/^#[0-9a-fA-F]{8}$/.test(value)) return value.slice(0, 7);
  return value;
}
