// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import { useFleetData } from './data/fleetGateway';
import type { FleetData, MaterialSlotSnapshot, PrinterViewModel, QueueViewModel } from './domain';
import { InventoryView } from './features/inventory/InventoryView';
import { PrinterDetailView } from './features/printers/PrinterDetailView';
import { printerRoute } from './features/printers/printerDetailViewModel';
import { changeInterfaceLanguage } from './i18n';
import {
  formatLocalizedRelativeTime,
  localizedMaterialUnit,
  localizedPresence,
  localizedPrinterStatus,
  localizedQueueState,
  localizedStatus,
} from './presentation/localization';
import {
  describeMaterialSource,
  formatDuration,
  formatPercent,
  printerTone,
  summarizeFleet,
} from './viewModel';

type NavItem = {
  path: string;
  icon: string;
  key: 'overview' | 'printers' | 'queue' | 'materials' | 'inventory' | 'farm' | 'system';
};

const navigation: NavItem[] = [
  { path: '/', icon: 'OV', key: 'overview' },
  { path: '/printers', icon: 'PR', key: 'printers' },
  { path: '/queue', icon: 'QU', key: 'queue' },
  { path: '/materials', icon: 'MT', key: 'materials' },
  { path: '/inventory', icon: 'SP', key: 'inventory' },
  { path: '/farm', icon: 'FM', key: 'farm' },
  { path: '/system', icon: 'SY', key: 'system' },
];

export function FoxForgeApp() {
  const fleet = useFleetData();
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const current = navigation.find((item) => item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)) ?? navigation[0];
  const openPrinter = (printerId: string) => navigate(printerRoute(printerId));

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">F</div>
          <div>
            <div className="brand-name">FoxForge</div>
            <div className="brand-subtitle">{t('shell.fleetControl')}</div>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navigation.map((item) => (
            <NavLink key={item.path} to={item.path} end={item.path === '/'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              <span>{t(`nav.${item.key}`)}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="runtime-status">
            <span className="status-dot good" />
            <div>
              <strong>{t('shell.developmentPreview')}</strong>
              <span>{t('shell.demoData')}</span>
            </div>
          </div>
          <a className="support-link" href="https://ko-fi.com/mikefox303" target="_blank" rel="noreferrer">
            <span aria-hidden="true">♡</span>
            <span>{t('shell.support')}</span>
            <span aria-hidden="true">↗</span>
          </a>
        </div>
      </aside>

      <main className="main-column">
        <header className="topbar">
          <div>
            <div className="eyebrow">{t('shell.workspace')}</div>
            <h1>{t(`nav.${current.key}`)}</h1>
          </div>
          <div className="topbar-actions">
            <div className="live-pill"><span className="status-dot good" /> {t('shell.preview')}</div>
            <button className="secondary-button" disabled title={t('shell.requiresApi')}>{t('shell.addPrinter')}</button>
          </div>
        </header>

        <div className="content">
          <Routes>
            <Route path="/" element={<OverviewView fleet={fleet} onOpenPrinter={openPrinter} />} />
            <Route path="/printers" element={<PrintersView fleet={fleet} onOpenPrinter={openPrinter} />} />
            <Route path="/printers/:printerId" element={<PrinterDetailView fleet={fleet} />} />
            <Route path="/queue" element={<QueueView fleet={fleet} />} />
            <Route path="/materials" element={<MaterialsView fleet={fleet} />} />
            <Route path="/inventory" element={<InventoryView fleet={fleet} />} />
            <Route path="/farm" element={<FarmView fleet={fleet} onOpenPrinter={openPrinter} />} />
            <Route path="/system" element={<SystemView />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function OverviewView({ fleet, onOpenPrinter }: { fleet: FleetData; onOpenPrinter: (printerId: string) => void }) {
  const { t } = useTranslation();
  const summary = useMemo(() => summarizeFleet(fleet), [fleet]);
  return (
    <div className="stack-xl">
      <section className="hero-panel">
        <div>
          <div className="eyebrow accent">{t('overview.eyebrow')}</div>
          <h2>{t('overview.title')}</h2>
          <p>{t('overview.subtitle')}</p>
        </div>
      </section>

      <section className="metric-grid">
        <Metric label={t('common.printers')} value={String(summary.totalPrinters)} detail={`${summary.connectedPrinters} ${t('common.connected')}`} />
        <Metric label={t('overview.printingNow')} value={String(summary.printingPrinters)} detail={t('overview.printingDetail')} />
        <Metric label={t('overview.waitingBlocked')} value={String(summary.queuedJobs)} detail={t('overview.waitingDetail')} />
        <Metric label={t('overview.materialAlerts')} value={String(summary.materialAlerts)} detail={t('overview.materialAlertsDetail')} warning={summary.materialAlerts > 0} />
      </section>

      <SectionHeader title={t('overview.fleet')} subtitle={t('overview.fleetSubtitle')} />
      <div className="printer-grid">
        {fleet.printers.map((printer) => <PrinterCard key={printer.identity.printerId} printer={printer} onOpen={() => onOpenPrinter(printer.identity.printerId)} />)}
      </div>

      <div className="two-column">
        <section className="panel">
          <SectionHeader title={t('overview.queuePulse')} subtitle={t('overview.queuePulseSubtitle')} />
          <div className="compact-list">{fleet.queue.map((entry) => <QueueRow key={entry.queueId} fleet={fleet} entry={entry} compact />)}</div>
        </section>
        <section className="panel">
          <SectionHeader title={t('overview.materialSystems')} subtitle={t('overview.materialSystemsSubtitle')} />
          <div className="compact-list">
            {fleet.printers.map((printer) => (
              <div className="material-summary" key={printer.identity.printerId}>
                <div><strong>{printer.identity.displayName}</strong><span>{describeMaterialSource(printer)}</span></div>
                <div className="slot-dots">{slotsFor(printer).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function PrintersView({ fleet, onOpenPrinter }: { fleet: FleetData; onOpenPrinter: (printerId: string) => void }) {
  const { t } = useTranslation();
  return (
    <div className="stack-lg">
      <SectionHeader title={t('printersPage.title')} subtitle={t('printersPage.subtitle')} />
      <div className="printer-grid">
        {fleet.printers.map((printer) => <PrinterCard key={printer.identity.printerId} printer={printer} onOpen={() => onOpenPrinter(printer.identity.printerId)} expanded />)}
      </div>
    </div>
  );
}

function QueueView({ fleet }: { fleet: FleetData }) {
  const { t } = useTranslation();
  return (
    <div className="stack-lg">
      <PageIntro eyebrow={t('queuePage.eyebrow')} title={t('queuePage.title')} text={t('queuePage.subtitle')} action={t('queuePage.addJob')} />
      <section className="panel table-panel">
        <div className="table-head queue-grid"><span>{t('queuePage.job')}</span><span>{t('queuePage.printer')}</span><span>{t('queuePage.state')}</span><span>{t('queuePage.attempts')}</span><span>{t('queuePage.updated')}</span></div>
        {fleet.queue.map((entry) => <QueueRow key={entry.queueId} fleet={fleet} entry={entry} />)}
      </section>
      <section className="callout warning"><strong>{t('queuePage.safetyTitle')}</strong><span>{t('queuePage.safetyText')}</span></section>
    </div>
  );
}

function MaterialsView({ fleet }: { fleet: FleetData }) {
  const { t } = useTranslation();
  return (
    <div className="stack-lg">
      <PageIntro eyebrow={t('materialsPage.eyebrow')} title={t('materialsPage.title')} text={t('materialsPage.subtitle')} />
      {fleet.printers.map((printer) => (
        <section className="panel" key={printer.identity.printerId}>
          <SectionHeader title={printer.identity.displayName} subtitle={`${printer.identity.vendor} ${printer.identity.model ?? ''}`} />
          {printer.materialSystem ? (
            <div className="material-units">
              {printer.materialSystem.units.map((unit) => (
                <div className="material-unit" key={unit.unitId}>
                  <div className="material-unit-head"><div><strong>{unit.label ?? localizedMaterialUnit(unit.kind, t)}</strong><span>{localizedMaterialUnit(unit.kind, t)}</span></div><span className="count-pill">{unit.slots.length} {t('common.slots')}</span></div>
                  <div className="slot-grid">{unit.slots.map((slot) => <MaterialSlot key={slot.slotId} slot={slot} />)}</div>
                </div>
              ))}
            </div>
          ) : <div className="empty-state">{t('materialsPage.unavailable')}</div>}
        </section>
      ))}
    </div>
  );
}

function FarmView({ fleet, onOpenPrinter }: { fleet: FleetData; onOpenPrinter: (printerId: string) => void }) {
  const { t } = useTranslation();
  const summary = summarizeFleet(fleet);
  const utilization = summary.totalPrinters ? Math.round((summary.printingPrinters / summary.totalPrinters) * 100) : 0;
  return (
    <div className="stack-lg">
      <section className="farm-hero">
        <div><div className="eyebrow accent">{t('farmPage.eyebrow')}</div><h2>{t('farmPage.connectedSummary', { active: summary.printingPrinters, connected: summary.connectedPrinters, total: summary.totalPrinters })}</h2><p>{t('farmPage.subtitle')}</p></div>
        <div className="farm-utilization"><span>{t('farmPage.utilization')}</span><strong>{utilization}%</strong></div>
      </section>
      <div className="farm-grid">
        {fleet.printers.map((printer) => (
          <article className="farm-tile" key={printer.identity.printerId}>
            <div className="farm-tile-head"><div><strong>{printer.identity.displayName}</strong><span>{printer.identity.vendor} · {printer.identity.model}</span></div><StatusBadge printer={printer} /></div>
            <div className="farm-info-row"><span>{describeMaterialSource(printer)}</span><span>{t('common.queuedCount', { count: fleet.queue.filter((entry) => entry.printerId === printer.identity.printerId).length })}</span></div>
            {printer.snapshot.activeJob ? <><div className="farm-job">{printer.snapshot.activeJob.name}</div><Progress value={printer.snapshot.activeJob.progress} /><div className="farm-job-meta"><span>{formatPercent(printer.snapshot.activeJob.progress)}</span><span>{formatDuration(printer.snapshot.activeJob.remainingSeconds)} {t('common.left')}</span></div></> : <div className="idle-surface">{t('common.readyForDispatch')}</div>}
            <div className="farm-tile-footer"><div className="slot-dots">{slotsFor(printer).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}</div><button className="text-button" onClick={() => onOpenPrinter(printer.identity.printerId)}>{t('common.openPrinter')} →</button></div>
          </article>
        ))}
      </div>
    </div>
  );
}

function SystemView() {
  const { i18n, t } = useTranslation();
  const active = (i18n.resolvedLanguage ?? i18n.language).slice(0, 2);
  return (
    <div className="stack-lg">
      <PageIntro eyebrow={t('systemPage.eyebrow')} title={t('systemPage.title')} text={t('systemPage.subtitle')} />
      <div className="system-card-grid">
        <section className="panel system-card"><span className="system-card-label">{t('systemPage.runtime')}</span><strong>{t('systemPage.developmentPreview')}</strong><p>{t('systemPage.runtimeText')}</p><div className="system-status-line"><span className="status-dot good" /> {t('systemPage.uiRunning')}</div></section>
        <section className="panel system-card"><span className="system-card-label">{t('systemPage.architecture')}</span><strong>{t('systemPage.parallelSafe')}</strong><p>{t('systemPage.parallelText')}</p><div className="system-status-line">backend / frontend / deployment</div></section>
        <section className="panel system-card language-card"><span className="system-card-label">{t('language.title')}</span><strong>{active.toUpperCase()}</strong><p>{t('systemPage.languageText')}</p><div className="language-switcher">{(['en', 'ru', 'uk'] as const).map((language) => <button key={language} className={active === language ? 'active' : ''} onClick={() => void changeInterfaceLanguage(language)}>{language.toUpperCase()}</button>)}</div></section>
      </div>
      <details className="diagnostics-panel panel"><summary>{t('systemPage.developerDiagnostics')}</summary><div className="definition-list diagnostics-list"><div><span>{t('systemPage.frontend')}</span><strong>React + TypeScript + Vite</strong></div><div><span>{t('systemPage.routing')}</span><strong>React Router</strong></div><div><span>{t('systemPage.serverState')}</span><strong>TanStack Query</strong></div><div><span>{t('systemPage.inventorySource')}</span><strong>{t('systemPage.inventorySourceValue')}</strong></div><div><span>{t('systemPage.backendApi')}</span><strong>{t('systemPage.notConnected')}</strong></div><div><span>{t('systemPage.realtime')}</span><strong>{t('systemPage.realtimeValue')}</strong></div></div></details>
    </div>
  );
}

function PrinterCard({ printer, onOpen, expanded = false }: { printer: PrinterViewModel; onOpen: () => void; expanded?: boolean }) {
  const { i18n, t } = useTranslation();
  const job = printer.snapshot.activeJob;
  return (
    <article className={`printer-card ${expanded ? 'expanded' : ''}`}>
      <div className="printer-card-head"><div><div className="vendor-label">{printer.identity.vendor}</div><h3>{printer.identity.displayName}</h3><span>{printer.identity.model ?? printer.identity.adapterKind}</span></div><StatusBadge printer={printer} /></div>
      {job ? <div className="job-block"><div className="job-title-row"><strong>{job.name ?? t('common.activeJob')}</strong><span>{formatPercent(job.progress)}</span></div><Progress value={job.progress} /><div className="job-meta"><span>{formatDuration(job.elapsedSeconds)} {t('common.elapsed')}</span><span>{formatDuration(job.remainingSeconds)} {t('common.left')}</span><span>{job.currentLayer ?? '—'} / {job.totalLayers ?? '—'} {t('common.layers')}</span></div></div> : <div className="idle-surface">{t('common.idleReady')}</div>}
      <div className="printer-info-strip"><div><span>{t('common.connection')}</span><strong>{localizedStatus(printer.snapshot.connection, t)}</strong></div><div><span>{t('common.material')}</span><strong>{describeMaterialSource(printer)}</strong></div><div><span>{t('common.updated')}</span><strong>{formatLocalizedRelativeTime(printer.snapshot.observedAt, i18n.resolvedLanguage ?? i18n.language)}</strong></div></div>
      <div className="printer-card-footer"><div className="slot-dots">{slotsFor(printer).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}</div><button className="text-button" onClick={onOpen}>{t('common.openPrinter')} →</button></div>
    </article>
  );
}

function QueueRow({ fleet, entry, compact = false }: { fleet: FleetData; entry: QueueViewModel; compact?: boolean }) {
  const { t } = useTranslation();
  const printer = fleet.printers.find((candidate) => candidate.identity.printerId === entry.printerId);
  if (compact) return <div className="compact-row"><div><strong>{entry.requestedName}</strong><span>{printer?.identity.displayName ?? entry.printerId}</span></div><span className={`queue-badge state-${entry.state}`}>{localizedQueueState(entry.state, t)}</span></div>;
  return <div className="table-row queue-grid"><div><strong>{entry.requestedName}</strong><span>{entry.filename} · {entry.format.toUpperCase()}</span>{entry.blocker && <small className="warning-text">{entry.blocker}</small>}</div><div><strong>{printer?.identity.displayName ?? entry.printerId}</strong><span>{printer?.identity.adapterKind ?? t('common.unknown')}</span></div><div><span className={`queue-badge state-${entry.state}`}>{localizedQueueState(entry.state, t)}</span></div><div><strong>{entry.attemptCount}</strong><span>{t('common.dispatchAttempts')}</span></div><div><strong>{new Date(entry.updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong><span>{new Date(entry.updatedAt).toLocaleDateString()}</span></div></div>;
}

function MaterialSlot({ slot }: { slot: MaterialSlotSnapshot }) {
  const { t } = useTranslation();
  const material = slot.detectedMaterial;
  const fraction = material?.remainingFraction;
  return <div className={`material-slot ${slot.activity === 'active' ? 'active' : ''}`}><div className="material-slot-head"><MaterialDot slot={slot} /><div><strong>{slot.label ?? `${t('common.slot')} ${slot.position + 1}`}</strong><span>{slot.activity === 'active' ? t('common.activeSource') : localizedPresence(slot.presence, t)}</span></div></div>{material ? <><div className="material-name">{[material.vendorName, material.productName ?? material.materialFamily].filter(Boolean).join(' ')}</div><div className="material-remaining">{fraction === undefined ? t('common.remainingUnknown') : `${Math.round(fraction * 100)}% ${t('common.remaining')}`}</div>{fraction !== undefined && <Progress value={fraction} compact />}</> : <div className="empty-slot-label">{t('common.empty')}</div>}</div>;
}

function MaterialDot({ slot }: { slot: MaterialSlotSnapshot }) {
  const value = slot.detectedMaterial?.rgbaHex;
  const color = value?.length === 9 ? value.slice(0, 7) : value ?? '#475569';
  const low = (slot.detectedMaterial?.remainingFraction ?? 1) <= 0.2;
  return <span className={`material-dot ${slot.activity === 'active' ? 'active' : ''} ${low ? 'low' : ''}`} style={{ background: color }} />;
}

function StatusBadge({ printer }: { printer: PrinterViewModel }) {
  const { t } = useTranslation();
  const tone = printerTone(printer);
  return <span className={`status-badge tone-${tone}`}><span className={`status-dot ${tone}`} />{localizedPrinterStatus(printer, t)}</span>;
}

function Progress({ value = 0, compact = false }: { value?: number; compact?: boolean }) {
  return <div className={`progress-track ${compact ? 'compact' : ''}`}><div className="progress-value" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></div>;
}

function Metric({ label, value, detail, warning = false }: { label: string; value: string; detail: string; warning?: boolean }) {
  return <article className={`metric-card ${warning ? 'tone-warning' : ''}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return <div className="section-header"><div><h2>{title}</h2><p>{subtitle}</p></div></div>;
}

function PageIntro({ eyebrow, title, text, action }: { eyebrow: string; title: string; text: string; action?: string }) {
  const { t } = useTranslation();
  return <div className="page-intro"><div><div className="eyebrow">{eyebrow}</div><h2>{title}</h2><p>{text}</p></div>{action && <button className="primary-button" disabled title={t('shell.requiresApi')}>{action}</button>}</div>;
}

function slotsFor(printer: PrinterViewModel): MaterialSlotSnapshot[] {
  return printer.materialSystem?.units.flatMap((unit) => unit.slots) ?? [];
}
