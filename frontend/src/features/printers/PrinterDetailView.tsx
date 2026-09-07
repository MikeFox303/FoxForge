// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import type { FleetData } from '../../domain';
import { SectionHeading } from '../../ui/SectionHeading';
import { formatPercent } from '../../viewModel';
import { MaterialSystemView } from './MaterialSystemView';
import { PrinterActiveJobPanel } from './PrinterActiveJobPanel';
import { PrinterOverviewView } from './PrinterOverviewView';
import { relativeTimeLabel } from './printerPresentation';
import { PrinterStatusBadge } from './PrinterStatusBadge';
import { ReconnectDiagnosticsPanel } from './ReconnectDiagnosticsPanel';
import {
  printerByRouteId,
  printerDetailTabs,
  type PrinterDetailTab,
  printerTelemetryPhase,
  queueForPrinter,
  summarizePrinterMaterials,
} from './printerDetailViewModel';

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
  const tabs = printerDetailTabs(printer);
  const selectedTab: PrinterDetailTab = tabs.includes(tab) ? tab : 'overview';

  const tabLabel = (item: PrinterDetailTab): string => (
    item === 'control' ? t('jobControl.controls') : t(`printerDetail.tabs.${item}`)
  );

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
          <PrinterStatusBadge printer={printer} />
          <span>{relativeTimeLabel(printer.snapshot.observedAt, t)}</span>
        </div>
      </section>

      <nav className="printer-detail-tabs" aria-label={t('printerDetail.sections')}>
        {tabs.map((item) => (
          <button key={item} className={selectedTab === item ? 'active' : ''} onClick={() => setTab(item)}>
            {tabLabel(item)}
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

      {selectedTab === 'overview' && (
        <PrinterOverviewView printer={printer} queue={queue} telemetryPhase={telemetryPhase} />
      )}

      {selectedTab === 'control' && tabs.includes('control') && (
        <section className="stack-lg printer-control-tab">
          <div className="printer-tab-intro">
            <div>
              <div className="eyebrow">{t('jobControl.controls')}</div>
              <h3>{job?.name ?? t('printerDetail.ready')}</h3>
              <p>{job ? t('printerDetail.capabilityText') : t('printerDetail.readyText')}</p>
            </div>
            {job && (
              <div className="printer-tab-stat">
                <strong>{formatPercent(job.progress)}</strong>
                <span>{t(`alpha.status.${job.state}`)}</span>
              </div>
            )}
          </div>

          {job ? (
            <PrinterActiveJobPanel printer={printer} controls />
          ) : (
            <section className="panel printer-ready-panel">
              <div className="ready-indicator"><span className={`status-dot ${telemetryPhase === 'live' ? 'good' : telemetryPhase === 'unavailable' ? 'danger' : 'warning'}`} /></div>
              <div>
                <h3>{t('printerDetail.ready')}</h3>
                <p>{t('printerDetail.readyText')}</p>
              </div>
            </section>
          )}
        </section>
      )}

      {selectedTab === 'materials' && tabs.includes('materials') && (
        <section className="stack-lg">
          <div className="printer-tab-intro">
            <div><div className="eyebrow">{t('printerDetail.materialSystem')}</div><h3>{t('printerDetail.materialsTitle')}</h3><p>{t('printerDetail.materialsText')}</p></div>
            <div className="printer-tab-stat"><strong>{materialSummary.loadedSlots}</strong><span>{t('printerDetail.loaded')}</span></div>
          </div>
          <MaterialSystemView printer={printer} />
        </section>
      )}

      {selectedTab === 'queue' && (
        <section className="panel table-panel printer-detail-queue-panel">
          <SectionHeading
            eyebrow={t('printerDetail.nextWork')}
            title={t('printerDetail.printerQueue')}
            trailing={<button className="primary-button" disabled title={t('printerDetail.requiresApi')}>{t('printerDetail.addJob')}</button>}
          />
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

      {selectedTab === 'diagnostics' && (
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
