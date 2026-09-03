// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { TFunction } from 'i18next';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import { useFleetData } from './data/fleetGateway';
import type { FleetData, MaterialSlotSnapshot, PrinterViewModel, QueueViewModel } from './domain';
import { InventoryView } from './features/inventory/InventoryView';
import { PrinterDetailView } from './features/printers/PrinterDetailView';
import { printerRoute } from './features/printers/printerDetailViewModel';
import { changeInterfaceLanguage } from './i18n';
import { formatDuration, formatPercent, printerTone, summarizeFleet } from './viewModel';

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
            <div className="brand-subtitle">{t('alpha.shell.fleetControl')}</div>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label={t('alpha.shell.primaryNavigation')}>
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
              <strong>{t('alpha.shell.build')}</strong>
              <span>{t('alpha.shell.liveApi')}</span>
            </div>
          </div>
          <a className="support-link" href="https://ko-fi.com/mikefox303" target="_blank" rel="noreferrer">
            <span aria-hidden="true">♡</span>
            <span>{t('alpha.shell.support')}</span>
            <span aria-hidden="true">↗</span>
          </a>
        </div>
      </aside>

      <main className="main-column">
        <header className="topbar">
          <div>
            <div className="eyebrow">{t('alpha.shell.workspace')}</div>
            <h1>{t(`nav.${current.key}`)}</h1>
          </div>
          <div className="topbar-actions">
            <div className="live-pill"><span className="status-dot good" /> {t('alpha.shell.liveApi')}</div>
            <button className="secondary-button" disabled title={t('alpha.shell.unavailableAlpha')}>{t('alpha.shell.addPrinter')}</button>
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
  const summary = useMemo(() => summarizeFleet(fleet), [fleet]);
  const { t } = useTranslation();
  return (
    <div className="stack-xl">
      <section className="hero-panel">
        <div>
          <div className="eyebrow accent">{t('alpha.overview.eyebrow')}</div>
          <h2>{t('alpha.overview.title')}</h2>
          <p>{t('alpha.overview.text')}</p>
        </div>
      </section>

      <section className="metric-grid">
        <Metric label={t('alpha.overview.printers')} value={String(summary.totalPrinters)} detail={t('alpha.overview.connected', { count: summary.connectedPrinters })} />
        <Metric label={t('alpha.overview.printingNow')} value={String(summary.printingPrinters)} detail={t('alpha.overview.acrossFleet')} />
        <Metric label={t('alpha.overview.waitingBlocked')} value={String(summary.queuedJobs)} detail={t('alpha.overview.queueNeedTurn')} />
        <Metric label={t('alpha.overview.materialAlerts')} value={String(summary.materialAlerts)} detail={t('alpha.overview.lowSlots')} warning={summary.materialAlerts > 0} />
      </section>

      <SectionHeader title={t('alpha.overview.fleet')} subtitle={t('alpha.overview.fleetSubtitle')} />
      <div className="printer-grid">
        {fleet.printers.map((printer) => <PrinterCard key={printer.identity.printerId} printer={printer} onOpen={() => onOpenPrinter(printer.identity.printerId)} />)}
      </div>

      <div className="two-column">
        <section className="panel">
          <SectionHeader title={t('alpha.overview.queuePulse')} subtitle={t('alpha.overview.queuePulseSubtitle')} />
          <div className="compact-list">{fleet.queue.map((entry) => <QueueRow key={entry.queueId} fleet={fleet} entry={entry} compact />)}</div>
        </section>
        <section className="panel">
          <SectionHeader title={t('alpha.overview.materialSystems')} subtitle={t('alpha.overview.materialSystemsSubtitle')} />
          <div className="compact-list">
            {fleet.printers.map((printer) => (
              <div className="material-summary" key={printer.identity.printerId}>
                <div><strong>{printer.identity.displayName}</strong><span>{materialSourceLabel(printer, t)}</span></div>
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
      <SectionHeader title={t('alpha.printers.title')} subtitle={t('alpha.printers.subtitle')} />
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
      <PageIntro eyebrow={t('alpha.queue.eyebrow')} title={t('alpha.queue.title')} text={t('alpha.queue.text')} action={t('alpha.queue.addJob')} />
      <section className="panel table-panel">
        <div className="table-head queue-grid"><span>{t('alpha.queue.job')}</span><span>{t('alpha.queue.printer')}</span><span>{t('alpha.queue.state')}</span><span>{t('alpha.queue.attempts')}</span><span>{t('alpha.queue.updated')}</span></div>
        {fleet.queue.map((entry) => <QueueRow key={entry.queueId} fleet={fleet} entry={entry} />)}
      </section>
      <section className="callout warning"><strong>{t('alpha.queue.indeterminateTitle')}</strong><span>{t('alpha.queue.indeterminateText')}</span></section>
    </div>
  );
}

function MaterialsView({ fleet }: { fleet: FleetData }) {
  const { t } = useTranslation();
  return (
    <div className="stack-lg">
      <PageIntro eyebrow={t('alpha.materials.eyebrow')} title={t('alpha.materials.title')} text={t('alpha.materials.text')} />
      {fleet.printers.map((printer) => (
        <section className="panel" key={printer.identity.printerId}>
          <SectionHeader title={printer.identity.displayName} subtitle={`${printer.identity.vendor} ${printer.identity.model ?? ''}`} />
          {printer.materialSystem ? (
            <div className="material-units">
              {printer.materialSystem.units.map((unit) => (
                <div className="material-unit" key={unit.unitId}>
                  <div className="material-unit-head"><div><strong>{unit.label ?? t('alpha.materials.materialUnit')}</strong><span>{friendlyUnit(unit.kind, t)}</span></div><span className="count-pill">{t('alpha.materials.slotCount', { count: unit.slots.length })}</span></div>
                  <div className="slot-grid">{unit.slots.map((slot) => <MaterialSlot key={slot.slotId} slot={slot} />)}</div>
                </div>
              ))}
            </div>
          ) : <div className="empty-state">{t('alpha.materials.unavailable')}</div>}
        </section>
      ))}
    </div>
  );
}

function FarmView({ fleet, onOpenPrinter }: { fleet: FleetData; onOpenPrinter: (printerId: string) => void }) {
  const summary = summarizeFleet(fleet);
  const utilization = summary.totalPrinters ? Math.round((summary.printingPrinters / summary.totalPrinters) * 100) : 0;
  const { t } = useTranslation();
  return (
    <div className="stack-lg">
      <section className="farm-hero">
        <div><div className="eyebrow accent">{t('alpha.farm.eyebrow')}</div><h2>{t('alpha.farm.activeConnected', { active: summary.printingPrinters, connected: summary.connectedPrinters, total: summary.totalPrinters })}</h2><p>{t('alpha.farm.text')}</p></div>
        <div className="farm-utilization"><span>{t('alpha.farm.utilization')}</span><strong>{utilization}%</strong></div>
      </section>
      <div className="farm-grid">
        {fleet.printers.map((printer) => (
          <article className="farm-tile" key={printer.identity.printerId}>
            <div className="farm-tile-head"><div><strong>{printer.identity.displayName}</strong><span>{printer.identity.vendor} · {printer.identity.model}</span></div><StatusBadge printer={printer} /></div>
            <div className="farm-info-row"><span>{materialSourceLabel(printer, t)}</span><span>{t('alpha.farm.queued', { count: fleet.queue.filter((entry) => entry.printerId === printer.identity.printerId).length })}</span></div>
            {printer.snapshot.activeJob ? <><div className="farm-job">{printer.snapshot.activeJob.name}</div><Progress value={printer.snapshot.activeJob.progress} /><div className="farm-job-meta"><span>{formatPercent(printer.snapshot.activeJob.progress)}</span><span>{formatDuration(printer.snapshot.activeJob.remainingSeconds)} {t('alpha.farm.left')}</span></div></> : <div className="idle-surface">{t('alpha.farm.ready')}</div>}
            <div className="farm-tile-footer"><div className="slot-dots">{slotsFor(printer).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}</div><button className="text-button" onClick={() => onOpenPrinter(printer.identity.printerId)}>{t('alpha.farm.openPrinter')}</button></div>
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
      <PageIntro eyebrow={t('alpha.system.eyebrow')} title={t('alpha.system.title')} text={t('alpha.system.text')} />
      <div className="system-card-grid">
        <section className="panel system-card"><span className="system-card-label">{t('alpha.system.runtime')}</span><strong>{t('alpha.system.runtimeTitle')}</strong><p>{t('alpha.system.runtimeText')}</p><div className="system-status-line"><span className="status-dot good" /> {t('alpha.system.uiRunning')}</div></section>
        <section className="panel system-card"><span className="system-card-label">{t('alpha.system.architecture')}</span><strong>{t('alpha.system.architectureTitle')}</strong><p>{t('alpha.system.architectureText')}</p><div className="system-status-line">backend / frontend / deployment</div></section>
        <section className="panel system-card language-card"><span className="system-card-label">{t('language.title')}</span><strong>{active.toUpperCase()}</strong><p>{t('alpha.system.languageText')}</p><div className="language-switcher">{(['en', 'ru', 'uk'] as const).map((language) => <button key={language} className={active === language ? 'active' : ''} onClick={() => void changeInterfaceLanguage(language)}>{language.toUpperCase()}</button>)}</div></section>
      </div>
      <details className="diagnostics-panel panel"><summary>{t('alpha.system.diagnostics')}</summary><div className="definition-list diagnostics-list"><div><span>{t('alpha.system.frontend')}</span><strong>React + TypeScript + Vite</strong></div><div><span>{t('alpha.system.routing')}</span><strong>React Router</strong></div><div><span>{t('alpha.system.serverState')}</span><strong>TanStack Query</strong></div><div><span>{t('alpha.system.inventorySource')}</span><strong>{t('alpha.system.inventoryLive')}</strong></div><div><span>{t('alpha.system.backendApi')}</span><strong>{t('alpha.system.apiConnected')}</strong></div><div><span>{t('alpha.system.realtime')}</span><strong>{t('alpha.system.realtimeReserved')}</strong></div></div></details>
    </div>
  );
}

function PrinterCard({ printer, onOpen, expanded = false }: { printer: PrinterViewModel; onOpen: () => void; expanded?: boolean }) {
  const job = printer.snapshot.activeJob;
  const { t } = useTranslation();
  return (
    <article className={`printer-card ${expanded ? 'expanded' : ''}`}>
      <div className="printer-card-head"><div><div className="vendor-label">{printer.identity.vendor}</div><h3>{printer.identity.displayName}</h3><span>{printer.identity.model ?? printer.identity.adapterKind}</span></div><StatusBadge printer={printer} /></div>
      {job ? <div className="job-block"><div className="job-title-row"><strong>{job.name ?? t('alpha.printer.activeJob')}</strong><span>{formatPercent(job.progress)}</span></div><Progress value={job.progress} /><div className="job-meta"><span>{formatDuration(job.elapsedSeconds)} {t('alpha.printer.elapsed')}</span><span>{formatDuration(job.remainingSeconds)} {t('alpha.printer.left')}</span><span>{job.currentLayer ?? '—'} / {job.totalLayers ?? '—'} {t('alpha.printer.layers')}</span></div></div> : <div className="idle-surface">{t('alpha.printer.idle')}</div>}
      <div className="printer-info-strip"><div><span>{t('alpha.printer.connection')}</span><strong>{t(`alpha.status.${printer.snapshot.connection}`)}</strong></div><div><span>{t('alpha.printer.material')}</span><strong>{materialSourceLabel(printer, t)}</strong></div><div><span>{t('alpha.printer.updated')}</span><strong>{relativeTimeLabel(printer.snapshot.observedAt, t)}</strong></div></div>
      <div className="printer-card-footer"><div className="slot-dots">{slotsFor(printer).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}</div><button className="text-button" onClick={onOpen}>{t('alpha.printer.open')}</button></div>
    </article>
  );
}

function QueueRow({ fleet, entry, compact = false }: { fleet: FleetData; entry: QueueViewModel; compact?: boolean }) {
  const printer = fleet.printers.find((candidate) => candidate.identity.printerId === entry.printerId);
  const { i18n, t } = useTranslation();
  const locale = i18n.resolvedLanguage ?? i18n.language;
  const state = t(`alpha.status.${entry.state}`);
  if (compact) return <div className="compact-row"><div><strong>{entry.requestedName}</strong><span>{printer?.identity.displayName ?? entry.printerId}</span></div><span className={`queue-badge state-${entry.state}`}>{state}</span></div>;
  return <div className="table-row queue-grid"><div><strong>{entry.requestedName}</strong><span>{entry.filename} · {entry.format.toUpperCase()}</span>{entry.blocker && <small className="warning-text">{entry.blocker}</small>}</div><div><strong>{printer?.identity.displayName ?? entry.printerId}</strong><span>{printer?.identity.adapterKind ?? t('alpha.status.unknown')}</span></div><div><span className={`queue-badge state-${entry.state}`}>{state}</span></div><div><strong>{entry.attemptCount}</strong><span>{t('alpha.queue.dispatchAttempts')}</span></div><div><strong>{new Date(entry.updatedAt).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })}</strong><span>{new Date(entry.updatedAt).toLocaleDateString(locale)}</span></div></div>;
}

function MaterialSlot({ slot }: { slot: MaterialSlotSnapshot }) {
  const material = slot.detectedMaterial;
  const fraction = material?.remainingFraction;
  const { t } = useTranslation();
  return <div className={`material-slot ${slot.activity === 'active' ? 'active' : ''}`}><div className="material-slot-head"><MaterialDot slot={slot} /><div><strong>{slot.label ?? t('alpha.materials.slot', { number: slot.position + 1 })}</strong><span>{slot.activity === 'active' ? t('alpha.materials.activeSource') : t(`alpha.status.${slot.presence}`)}</span></div></div>{material ? <><div className="material-name">{[material.vendorName, material.productName ?? material.materialFamily].filter(Boolean).join(' ')}</div><div className="material-remaining">{fraction === undefined ? t('alpha.materials.remainingUnknown') : t('alpha.materials.remaining', { value: Math.round(fraction * 100) })}</div>{fraction !== undefined && <Progress value={fraction} compact />}</> : <div className="empty-slot-label">{t('alpha.materials.empty')}</div>}</div>;
}

function MaterialDot({ slot }: { slot: MaterialSlotSnapshot }) {
  const value = slot.detectedMaterial?.rgbaHex;
  const color = value?.length === 9 ? value.slice(0, 7) : value ?? '#475569';
  const low = (slot.detectedMaterial?.remainingFraction ?? 1) <= 0.2;
  return <span className={`material-dot ${slot.activity === 'active' ? 'active' : ''} ${low ? 'low' : ''}`} style={{ background: color }} />;
}

function StatusBadge({ printer }: { printer: PrinterViewModel }) {
  const tone = printerTone(printer);
  const { t } = useTranslation();
  const key = printer.snapshot.stale ? 'stale' : printer.snapshot.connection !== 'connected' ? printer.snapshot.connection : printer.snapshot.operationalState;
  return <span className={`status-badge tone-${tone}`}><span className={`status-dot ${tone}`} />{t(`alpha.status.${key}`)}</span>;
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
  return <div className="page-intro"><div><div className="eyebrow">{eyebrow}</div><h2>{title}</h2><p>{text}</p></div>{action && <button className="primary-button" disabled title={t('alpha.shell.unavailableAlpha')}>{action}</button>}</div>;
}

function slotsFor(printer: PrinterViewModel): MaterialSlotSnapshot[] {
  return printer.materialSystem?.units.flatMap((unit) => unit.slots) ?? [];
}

function friendlyUnit(kind: string, t: TFunction): string {
  if (kind === 'multi_slot') return t('alpha.materials.multiSlot');
  if (kind === 'external') return t('alpha.materials.external');
  if (kind === 'toolhead') return t('alpha.materials.toolhead');
  return t('alpha.materials.materialUnit');
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
