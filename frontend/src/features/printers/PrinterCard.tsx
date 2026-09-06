// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { TFunction } from 'i18next';
import { useTranslation } from 'react-i18next';

import type { MaterialSlotSnapshot, PrinterViewModel } from '../../domain';
import { formatDuration, formatPercent, printerTone } from '../../viewModel';

export type PrinterCardDensity = 'compact' | 'standard' | 'detailed';

export interface PrinterCardProps {
  printer: PrinterViewModel;
  queueCount: number;
  onOpen: () => void;
  density?: PrinterCardDensity;
}

export function PrinterCard({ printer, queueCount, onOpen, density = 'standard' }: PrinterCardProps) {
  const job = printer.snapshot.activeJob;
  const { t } = useTranslation();
  const detailed = density === 'detailed';
  const compact = density === 'compact';

  return (
    <article className={`printer-card density-${density} ${detailed ? 'expanded' : ''}`}>
      <div className="printer-card-head">
        <div>
          <div className="vendor-label">{printer.identity.vendor}</div>
          <h3>{printer.identity.displayName}</h3>
          <span>{printer.identity.model ?? printer.identity.adapterKind}</span>
        </div>
        <PrinterStatusBadge printer={printer} />
      </div>

      {job ? (
        <div className="job-block">
          <div className="job-title-row">
            <strong>{job.name ?? t('alpha.printer.activeJob')}</strong>
            <span>{formatPercent(job.progress)}</span>
          </div>
          <Progress value={job.progress} />
          {!compact && (
            <div className="job-meta">
              <span>{formatDuration(job.elapsedSeconds)} {t('alpha.printer.elapsed')}</span>
              <span>{formatDuration(job.remainingSeconds)} {t('alpha.printer.left')}</span>
              <span>{job.currentLayer ?? '—'} / {job.totalLayers ?? '—'} {t('alpha.printer.layers')}</span>
            </div>
          )}
        </div>
      ) : <div className="idle-surface">{t('alpha.printer.idle')}</div>}

      {!compact && (
        <div className="printer-info-strip">
          <div><span>{t('alpha.printer.connection')}</span><strong>{t(`alpha.status.${printer.snapshot.connection}`)}</strong></div>
          <div><span>{t('alpha.printer.material')}</span><strong>{materialSourceLabel(printer, t)}</strong></div>
          <div><span>{t('alpha.printer.updated')}</span><strong>{relativeTimeLabel(printer.snapshot.observedAt, t)}</strong></div>
        </div>
      )}

      <div className="printer-card-footer">
        <div className="printer-card-sources">
          <div className="slot-dots">{slotsFor(printer).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}</div>
          <span className="count-pill">{t('alpha.farm.queued', { count: queueCount })}</span>
        </div>
        <button className="text-button" type="button" onClick={onOpen}>{t('alpha.printer.open')}</button>
      </div>
    </article>
  );
}

function PrinterStatusBadge({ printer }: { printer: PrinterViewModel }) {
  const tone = printerTone(printer);
  const { t } = useTranslation();
  const key = printer.snapshot.stale
    ? 'stale'
    : printer.snapshot.connection !== 'connected'
      ? printer.snapshot.connection
      : printer.snapshot.operationalState;
  return <span className={`status-badge tone-${tone}`}><span className={`status-dot ${tone}`} />{t(`alpha.status.${key}`)}</span>;
}

function Progress({ value = 0 }: { value?: number }) {
  return <div className="progress-track"><div className="progress-value" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></div>;
}

function MaterialDot({ slot }: { slot: MaterialSlotSnapshot }) {
  const value = slot.detectedMaterial?.rgbaHex;
  const color = value?.length === 9 ? value.slice(0, 7) : value ?? '#475569';
  const low = (slot.detectedMaterial?.remainingFraction ?? 1) <= 0.2;
  return <span className={`material-dot ${slot.activity === 'active' ? 'active' : ''} ${low ? 'low' : ''}`} style={{ background: color }} />;
}

function slotsFor(printer: PrinterViewModel): MaterialSlotSnapshot[] {
  return printer.materialSystem?.units.flatMap((unit) => unit.slots) ?? [];
}

function materialSourceLabel(printer: PrinterViewModel, t: TFunction): string {
  const slots = slotsFor(printer);
  const active = slots.find((slot) => slot.activity === 'active' && slot.detectedMaterial);
  const loaded = slots.find((slot) => slot.presence === 'loaded' && slot.detectedMaterial);
  const material = (active ?? loaded)?.detectedMaterial;
  if (!material) return t('alpha.materialSource.none');
  return [material.materialFamily, material.vendorName].filter(Boolean).join(' · ') || t('alpha.materialSource.loaded');
}

function relativeTimeLabel(observedAt: string, t: TFunction, nowMs: number = Date.now()): string {
  const observedMs = Date.parse(observedAt);
  if (Number.isNaN(observedMs)) return t('alpha.relative.recently');
  const deltaMs = Math.max(0, nowMs - observedMs);
  if (deltaMs < 60_000) return t('alpha.relative.justNow');
  if (deltaMs < 3_600_000) return t('alpha.relative.minutes', { count: Math.floor(deltaMs / 60_000) });
  if (deltaMs < 86_400_000) return t('alpha.relative.hours', { count: Math.floor(deltaMs / 3_600_000) });
  return t('alpha.relative.days', { count: Math.floor(deltaMs / 86_400_000) });
}
