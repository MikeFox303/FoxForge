// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import type { FleetData, MaterialSlotSnapshot, PrinterViewModel } from '../../domain';
import {
  describeMaterialSource,
  formatDuration,
  formatPercent,
  formatRelativeTime,
  printerStatusLabel,
  printerTone,
} from '../../viewModel';
import { JobControlActions } from './JobControlActions';
import { ReconnectDiagnosticsPanel } from './ReconnectDiagnosticsPanel';
import {
  materialSlots,
  printerByRouteId,
  printerTelemetryPhase,
  queueForPrinter,
  summarizePrinterMaterials,
} from './printerDetailViewModel';

type PrinterDetailTab = 'overview' | 'materials' | 'queue' | 'diagnostics';

export function PrinterDetailView({ fleet }: { fleet: FleetData }) {
  const { printerId } = useParams();
  const printer = printerByRouteId(fleet, printerId);
  const navigate = useNavigate();
  const { i18n, t } = useTranslation();
  const [tab, setTab] = useState<PrinterDetailTab>('overview');

  if (!printer) {
    return (
      <section className="panel printer-not-found">
        <div>
          <div className="eyebrow">{t('printerDetail.notFoundEyebrow')}</div>
          <h2>{t('printerDetail.notFound')}</h2>
          <p>{t('printerDetail.notFoundText')}</p>
        </div>
        <button className="secondary-button" onClick={() => navigate('/printers')}>{t('printerDetail.backToPrinters')}</button>
      </section>
    );
  }

  const job = printer.snapshot.activeJob;
  const queue = queueForPrinter(fleet, printer.identity.printerId);
  const materialSummary = summarizePrinterMaterials(printer);
  const telemetryPhase = printerTelemetryPhase(printer);
  const locale = i18n.resolvedLanguage ?? i18n.language;

  return (
    <div className="stack-lg printer-detail-page">
      <section className="printer-detail-hero">
        <div className="printer-detail-title-row">
          <button className="printer-back-button" onClick={() => navigate('/printers')} aria-label={t('printerDetail.backToPrinters')}>←</button>
          <div className="printer-detail-title">
            <div className="vendor-label">{printer.identity.vendor}</div>
            <h2>{printer.identity.displayName}</h2>
            <p>{printer.identity.model ?? t('printerDetail.unknownModel')}</p>
          </div>
        </div>
        <div className="printer-detail-hero-status">
          <StatusBadge printer={printer} />
          <span>{formatRelativeTime(printer.snapshot.observedAt)}</span>
        </div>
      </section>

      <nav className="printer-detail-tabs" aria-label={t('printerDetail.sections')}>
        {(['overview', 'materials', 'queue', 'diagnostics'] as PrinterDetailTab[]).map((item) => (
          <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>
            {t(`printerDetail.tabs.${item}`)}
            {item === 'queue' && queue.length > 0 && <span>{queue.length}</span>}
          </button>
        ))}
      </nav>

      {telemetryPhase !== 'live' && (
        <section className={`runtime-notice ${telemetryPhase === 'unavailable' ? 'error' : 'loading'}`} role="status" aria-live="polite">
          <span className={`status-dot ${telemetryPhase === 'unavailable' ? 'danger' : 'warning'}`} aria-hidden="true" />
          <div>
            <strong>{t(`printerDetail.telemetry.${telemetryPhase}Title`)}</strong>
            <span>{t(`printerDetail.telemetry.${telemetryPhase}Text`)}</span>
          </div>
        </section>
      )}

      {tab === 'overview' && (
        <div className="stack-lg">
          <section className="printer-detail-kpis">
            <DetailKpi label={t('printerDetail.connection')} value={t(`alpha.status.${printer.snapshot.connection}`)} />
            <DetailKpi label={t('printerDetail.state')} value={t(`alpha.status.${printerStatusLabel(printer)}`)} />
            <DetailKpi label={t('printerDetail.material')} value={describeMaterialSource(printer)} />
            <DetailKpi label={t('printerDetail.queue')} value={queue.length ? `${queue.length}` : t('printerDetail.clear')} />
          </section>

          {job ? (
            <section className="panel printer-active-job">
              <div className="printer-section-heading">
                <div>
                  <div className="eyebrow">{t('printerDetail.activeJob')}</div>
                  <h3>{job.name ?? t('printerDetail.unnamedJob')}</h3>
                </div>
                <strong className="printer-job-percent">{formatPercent(job.progress)}</strong>
              </div>
              <Progress value={job.progress} />
              <div className="printer-job-facts">
                <Fact label={t('printerDetail.elapsed')} value={formatDuration(job.elapsedSeconds)} />
                <Fact label={t('printerDetail.remainingTime')} value={formatDuration(job.remainingSeconds)} />
                <Fact label={t('printerDetail.layer')} value={`${job.currentLayer ?? '—'} / ${job.totalLayers ?? '—'}`} />
                <Fact label={t('printerDetail.jobState')} value={t(`alpha.status.${job.state}`)} />
              </div>
              <JobControlActions printer={printer} />
            </section>
          ) : (
            <section className="panel printer-ready-panel">
              <div className="ready-indicator"><span className={`status-dot ${telemetryPhase === 'live' ? 'good' : telemetryPhase === 'unavailable' ? 'danger' : 'warning'}`} /></div>
              <div>
                <h3>{telemetryPhase === 'live' ? t('printerDetail.ready') : t(`printerDetail.telemetry.${telemetryPhase}Title`)}</h3>
                <p>{telemetryPhase === 'live' ? t('printerDetail.readyText') : t(`printerDetail.telemetry.${telemetryPhase}Text`)}</p>
              </div>
            </section>
          )}

          <div className="two-column printer-detail-columns">
            <section className="panel">
              <div className="printer-section-heading compact-heading">
                <div><div className="eyebrow">{t('printerDetail.materialSystem')}</div><h3>{t('printerDetail.loadedMaterials')}</h3></div>
                <span>{materialSummary.loadedSlots}/{materialSummary.totalSlots}</span>
              </div>
              {printer.materialSystem ? (
                <div className="printer-material-summary-list">
                  {printer.materialSystem.units.map((unit) => (
                    <div className="printer-material-summary-row" key={unit.unitId}>
                      <div>
                        <strong>{unit.label ?? t(`alpha.materials.${materialUnitKey(unit.kind)}`)}</strong>
                        <span>{unit.slots.filter((slot) => slot.presence === 'loaded').length} {t('printerDetail.loaded').toLocaleLowerCase()}</span>
                      </div>
                      <div className="slot-dots">{unit.slots.map((slot) => <MaterialDot slot={slot} key={slot.slotId} />)}</div>
                    </div>
                  ))}
                </div>
              ) : <div className="empty-state">{t('printerDetail.noMaterialData')}</div>}
              {materialSummary.lowSlots > 0 && <div className="printer-inline-warning">{materialSummary.lowSlots} {t('printerDetail.lowMaterial')}</div>}
            </section>

            <section className="panel">
              <div className="printer-section-heading compact-heading">
                <div><div className="eyebrow">{t('printerDetail.nextWork')}</div><h3>{t('printerDetail.printerQueue')}</h3></div>
                <span>{queue.length}</span>
              </div>
              {queue.length ? (
                <div className="printer-queue-compact">
                  {queue.slice(0, 4).map((entry) => (
                    <div key={entry.queueId}>
                      <div><strong>{entry.requestedName}</strong><span>{entry.filename}</span></div>
                      <span className={`queue-badge state-${entry.state}`}>{t(`alpha.status.${entry.state}`)}</span>
                    </div>
                  ))}
                </div>
              ) : <div className="empty-state">{t('printerDetail.queueEmpty')}</div>}
            </section>
          </div>

          <section className="printer-capability-note">
            <div>
              <strong>{t('printerDetail.capabilityTitle')}</strong>
              <span>{t('printerDetail.capabilityText')}</span>
            </div>
          </section>
        </div>
      )}

      {tab === 'materials' && (
        <section className="stack-lg">
          <div className="printer-tab-intro">
            <div><div className="eyebrow">{t('printerDetail.materialSystem')}</div><h3>{t('printerDetail.materialsTitle')}</h3><p>{t('printerDetail.materialsText')}</p></div>
            <div className="printer-tab-stat"><strong>{materialSummary.loadedSlots}</strong><span>{t('printerDetail.loaded')}</span></div>
          </div>
          {printer.materialSystem?.units.map((unit) => (
            <section className="panel" key={unit.unitId}>
              <div className="material-unit-head">
                <div><strong>{unit.label ?? t(`alpha.materials.${materialUnitKey(unit.kind)}`)}</strong><span>{t(`alpha.materials.${materialUnitKey(unit.kind)}`)}</span></div>
                <span className="count-pill">{t('alpha.materials.slotCount', { count: unit.slots.length })}</span>
              </div>
              <div className="slot-grid printer-detail-slot-grid">{unit.slots.map((slot) => <MaterialSlot slot={slot} key={slot.slotId} />)}</div>
            </section>
          )) ?? <div className="panel empty-state">{t('printerDetail.noMaterialData')}</div>}
        </section>
      )}

      {tab === 'queue' && (
        <section className="panel table-panel printer-detail-queue-panel">
          <div className="printer-section-heading">
            <div><div className="eyebrow">{t('printerDetail.nextWork')}</div><h3>{t('printerDetail.printerQueue')}</h3></div>
            <button className="primary-button" disabled title={t('printerDetail.requiresApi')}>{t('printerDetail.addJob')}</button>
          </div>
          {queue.length ? (
            <div className="printer-queue-table">
              {queue.map((entry) => (
                <div className="printer-queue-table-row" key={entry.queueId}>
                  <div><strong>{entry.requestedName}</strong><span>{entry.filename} · {entry.format.toUpperCase()}</span>{entry.blocker && <small>{entry.blocker}</small>}</div>
                  <span className={`queue-badge state-${entry.state}`}>{t(`alpha.status.${entry.state}`)}</span>
                  <div><strong>{entry.attemptCount}</strong><span>{t('printerDetail.attempts')}</span></div>
                  <div><strong>{new Date(entry.updatedAt).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })}</strong><span>{new Date(entry.updatedAt).toLocaleDateString(locale)}</span></div>
                </div>
              ))}
            </div>
          ) : <div className="empty-state">{t('printerDetail.queueEmpty')}</div>}
        </section>
      )}

      {tab === 'diagnostics' && (
        <div className="two-column printer-diagnostics-grid">
          <section className="panel definition-list">
            <div><span>{t('printerDetail.diagnostics.printerId')}</span><strong>{printer.identity.printerId}</strong></div>
            <div><span>{t('printerDetail.diagnostics.adapter')}</span><strong>{printer.identity.adapterKind}</strong></div>
            <div><span>{t('printerDetail.diagnostics.connection')}</span><strong>{t(`alpha.status.${printer.snapshot.connection}`)}</strong></div>
            <div><span>{t('printerDetail.diagnostics.observed')}</span><strong>{printer.snapshot.observedAt}</strong></div>
            <div><span>{t('printerDetail.diagnostics.stale')}</span><strong>{t(`printerDetail.diagnostics.${printer.snapshot.stale ? 'yes' : 'no'}`)}</strong></div>
          </section>
          <section className="panel definition-list">
            {printer.capabilities.length ? printer.capabilities.map((capability) => (
              <div key={capability.capabilityId}><span>{capability.label}</span><strong>{capability.capabilityId} · v{capability.majorVersion}</strong></div>
            )) : <div><span>{t('printerDetail.diagnostics.capabilities')}</span><strong>{t('printerDetail.diagnostics.noneAdvertised')}</strong></div>}
          </section>
          <ReconnectDiagnosticsPanel printerId={printer.identity.printerId} />
        </div>
      )}
    </div>
  );
}

function DetailKpi({ label, value }: { label: string; value: string }) {
  return <article className="printer-detail-kpi"><span>{label}</span><strong>{value}</strong></article>;
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function StatusBadge({ printer }: { printer: PrinterViewModel }) {
  const tone = printerTone(printer);
  const { t } = useTranslation();
  return <span className={`status-badge tone-${tone}`}><span className={`status-dot ${tone}`} />{t(`alpha.status.${printerStatusLabel(printer)}`)}</span>;
}

function Progress({ value = 0 }: { value?: number }) {
  return <div className="progress-track"><div className="progress-value" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></div>;
}

function MaterialDot({ slot }: { slot: MaterialSlotSnapshot }) {
  const source = slot.detectedMaterial?.rgbaHex;
  const color = source?.length === 9 ? source.slice(0, 7) : source ?? '#475569';
  const low = (slot.detectedMaterial?.remainingFraction ?? 1) <= 0.2;
  return <span className={`material-dot ${slot.activity === 'active' ? 'active' : ''} ${low ? 'low' : ''}`} style={{ background: color }} />;
}

function MaterialSlot({ slot }: { slot: MaterialSlotSnapshot }) {
  const { t } = useTranslation();
  const material = slot.detectedMaterial;
  const fraction = material?.remainingFraction;
  return (
    <article className={`material-slot printer-detail-slot ${slot.activity === 'active' ? 'active' : ''}`}>
      <div className="material-slot-head">
        <MaterialDot slot={slot} />
        <div><strong>{slot.label ?? t('alpha.materials.slot', { number: slot.position + 1 })}</strong><span>{slot.activity === 'active' ? t('printerDetail.activeSource') : t(`alpha.status.${slot.presence}`)}</span></div>
      </div>
      {material ? (
        <>
          <div className="material-name">{[material.vendorName, material.productName ?? material.materialFamily].filter(Boolean).join(' ')}</div>
          <div className="material-remaining">{fraction === undefined ? t('printerDetail.remainingUnknown') : `${Math.round(fraction * 100)}% ${t('printerDetail.remaining').toLocaleLowerCase()}`}</div>
          {fraction !== undefined && <Progress value={fraction} />}
        </>
      ) : <div className="empty-slot-label">{t('printerDetail.empty')}</div>}
    </article>
  );
}

function materialUnitKey(kind: string): 'multiSlot' | 'external' | 'toolhead' | 'materialUnit' {
  if (kind === 'multi_slot') return 'multiSlot';
  if (kind === 'external') return 'external';
  if (kind === 'toolhead') return 'toolhead';
  return 'materialUnit';
}
