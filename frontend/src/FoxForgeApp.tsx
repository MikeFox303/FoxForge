// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom';

import { useFleetData } from './data/fleetGateway';
import type { FleetData, MaterialSlotSnapshot, PrinterViewModel, QueueViewModel } from './domain';
import { InventoryView } from './features/inventory/InventoryView';
import { changeInterfaceLanguage } from './i18n';
import {
  describeMaterialSource,
  findPrinter,
  formatDuration,
  formatPercent,
  formatRelativeTime,
  printerStatusLabel,
  printerTone,
  summarizeFleet,
} from './viewModel';

type PrinterTab = 'overview' | 'materials' | 'diagnostics';

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
  const [selectedPrinterId, setSelectedPrinterId] = useState<string | null>(null);
  const selectedPrinter = selectedPrinterId ? findPrinter(fleet, selectedPrinterId) : undefined;
  const location = useLocation();
  const { t } = useTranslation();
  const current = navigation.find((item) => item.path === location.pathname) ?? navigation[0];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">F</div>
          <div>
            <div className="brand-name">FoxForge</div>
            <div className="brand-subtitle">Fleet control</div>
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
            <button className="secondary-button" disabled title="Requires the public API">{t('shell.addPrinter')}</button>
          </div>
        </header>

        <div className="content">
          <Routes>
            <Route path="/" element={<OverviewView fleet={fleet} onOpenPrinter={setSelectedPrinterId} />} />
            <Route path="/printers" element={<PrintersView fleet={fleet} onOpenPrinter={setSelectedPrinterId} />} />
            <Route path="/queue" element={<QueueView fleet={fleet} />} />
            <Route path="/materials" element={<MaterialsView fleet={fleet} />} />
            <Route path="/inventory" element={<InventoryView fleet={fleet} />} />
            <Route path="/farm" element={<FarmView fleet={fleet} onOpenPrinter={setSelectedPrinterId} />} />
            <Route path="/system" element={<SystemView />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>

      {selectedPrinter && <PrinterDrawer fleet={fleet} printer={selectedPrinter} onClose={() => setSelectedPrinterId(null)} />}
    </div>
  );
}

function OverviewView({ fleet, onOpenPrinter }: { fleet: FleetData; onOpenPrinter: (printerId: string) => void }) {
  const summary = useMemo(() => summarizeFleet(fleet), [fleet]);
  return (
    <div className="stack-xl">
      <section className="hero-panel">
        <div>
          <div className="eyebrow accent">Mixed fleet, one workspace</div>
          <h2>Your printers, jobs and materials in one place.</h2>
          <p>Common workflows stay consistent while typed capabilities preserve deep vendor-specific features.</p>
        </div>
      </section>

      <section className="metric-grid">
        <Metric label="Printers" value={String(summary.totalPrinters)} detail={`${summary.connectedPrinters} connected`} />
        <Metric label="Printing now" value={String(summary.printingPrinters)} detail="Across the fleet" />
        <Metric label="Waiting / blocked" value={String(summary.queuedJobs)} detail="Queue entries needing a turn" />
        <Metric label="Material alerts" value={String(summary.materialAlerts)} detail="Loaded slots at or below 20%" warning={summary.materialAlerts > 0} />
      </section>

      <SectionHeader title="Fleet" subtitle="Current status, active jobs and loaded materials." />
      <div className="printer-grid">
        {fleet.printers.map((printer) => <PrinterCard key={printer.identity.printerId} printer={printer} onOpen={() => onOpenPrinter(printer.identity.printerId)} />)}
      </div>

      <div className="two-column">
        <section className="panel">
          <SectionHeader title="Queue pulse" subtitle="Running, waiting and blocked work." />
          <div className="compact-list">{fleet.queue.map((entry) => <QueueRow key={entry.queueId} fleet={fleet} entry={entry} compact />)}</div>
        </section>
        <section className="panel">
          <SectionHeader title="Material systems" subtitle="Physical material currently reported by printers." />
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
  return (
    <div className="stack-lg">
      <SectionHeader title="Printers" subtitle="Status, jobs and loaded materials across every adapter." />
      <div className="printer-grid">
        {fleet.printers.map((printer) => <PrinterCard key={printer.identity.printerId} printer={printer} onOpen={() => onOpenPrinter(printer.identity.printerId)} expanded />)}
      </div>
    </div>
  );
}

function QueueView({ fleet }: { fleet: FleetData }) {
  return (
    <div className="stack-lg">
      <PageIntro eyebrow="Safe print scheduling" title="Print queue" text="Blocked and uncertain starts stay explicit instead of being collapsed into generic errors." action="Add job" />
      <section className="panel table-panel">
        <div className="table-head queue-grid"><span>Job</span><span>Printer</span><span>State</span><span>Attempts</span><span>Updated</span></div>
        {fleet.queue.map((entry) => <QueueRow key={entry.queueId} fleet={fleet} entry={entry} />)}
      </section>
      <section className="callout warning"><strong>Indeterminate remains a safety state</strong><span>FoxForge never blindly starts a job again when it cannot prove whether the previous dispatch reached the printer.</span></section>
    </div>
  );
}

function MaterialsView({ fleet }: { fleet: FleetData }) {
  return (
    <div className="stack-lg">
      <PageIntro eyebrow="Physical material state" title="Materials" text="What printers currently report as loaded, active or empty. Inventory ownership remains a separate FoxForge context." />
      {fleet.printers.map((printer) => (
        <section className="panel" key={printer.identity.printerId}>
          <SectionHeader title={printer.identity.displayName} subtitle={`${printer.identity.vendor} ${printer.identity.model ?? ''}`} />
          {printer.materialSystem ? (
            <div className="material-units">
              {printer.materialSystem.units.map((unit) => (
                <div className="material-unit" key={unit.unitId}>
                  <div className="material-unit-head"><div><strong>{unit.label ?? unit.kind}</strong><span>{friendlyUnit(unit.kind)}</span></div><span className="count-pill">{unit.slots.length} slot{unit.slots.length === 1 ? '' : 's'}</span></div>
                  <div className="slot-grid">{unit.slots.map((slot) => <MaterialSlot key={slot.slotId} slot={slot} />)}</div>
                </div>
              ))}
            </div>
          ) : <div className="empty-state">Material information is not available.</div>}
        </section>
      ))}
    </div>
  );
}

function FarmView({ fleet, onOpenPrinter }: { fleet: FleetData; onOpenPrinter: (printerId: string) => void }) {
  const summary = summarizeFleet(fleet);
  const utilization = summary.totalPrinters ? Math.round((summary.printingPrinters / summary.totalPrinters) * 100) : 0;
  return (
    <div className="stack-lg">
      <section className="farm-hero">
        <div><div className="eyebrow accent">Farm command center</div><h2>{summary.printingPrinters} active · {summary.connectedPrinters}/{summary.totalPrinters} connected</h2><p>Dense fleet monitoring without vendor-specific branching.</p></div>
        <div className="farm-utilization"><span>Current utilization</span><strong>{utilization}%</strong></div>
      </section>
      <div className="farm-grid">
        {fleet.printers.map((printer) => (
          <article className="farm-tile" key={printer.identity.printerId}>
            <div className="farm-tile-head"><div><strong>{printer.identity.displayName}</strong><span>{printer.identity.vendor} · {printer.identity.model}</span></div><StatusBadge printer={printer} /></div>
            <div className="farm-info-row"><span>{describeMaterialSource(printer)}</span><span>{fleet.queue.filter((entry) => entry.printerId === printer.identity.printerId).length} queued</span></div>
            {printer.snapshot.activeJob ? <><div className="farm-job">{printer.snapshot.activeJob.name}</div><Progress value={printer.snapshot.activeJob.progress} /><div className="farm-job-meta"><span>{formatPercent(printer.snapshot.activeJob.progress)}</span><span>{formatDuration(printer.snapshot.activeJob.remainingSeconds)} left</span></div></> : <div className="idle-surface">Ready for dispatch</div>}
            <div className="farm-tile-footer"><div className="slot-dots">{slotsFor(printer).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}</div><button className="text-button" onClick={() => onOpenPrinter(printer.identity.printerId)}>Open printer →</button></div>
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
      <PageIntro eyebrow="Application status" title="System" text="Runtime, deployment and interface preferences. Developer details stay secondary." />
      <div className="system-card-grid">
        <section className="panel system-card"><span className="system-card-label">Runtime</span><strong>Development preview</strong><p>UI reads representative data through query gateways while the public API is built.</p><div className="system-status-line"><span className="status-dot good" /> UI running</div></section>
        <section className="panel system-card"><span className="system-card-label">Architecture</span><strong>Parallel-safe UI</strong><p>Frontend work consumes merged contracts only; backend branches remain non-authoritative until they enter main.</p><div className="system-status-line">backend / frontend / deployment</div></section>
        <section className="panel system-card language-card"><span className="system-card-label">{t('language.title')}</span><strong>{active.toUpperCase()}</strong><p>English, Russian and Ukrainian share one component tree.</p><div className="language-switcher">{(['en', 'ru', 'uk'] as const).map((language) => <button key={language} className={active === language ? 'active' : ''} onClick={() => void changeInterfaceLanguage(language)}>{language.toUpperCase()}</button>)}</div></section>
      </div>
      <details className="diagnostics-panel panel"><summary>Developer diagnostics</summary><div className="definition-list diagnostics-list"><div><span>Frontend</span><strong>React + TypeScript + Vite</strong></div><div><span>Routing</span><strong>React Router</strong></div><div><span>Server state</span><strong>TanStack Query</strong></div><div><span>Inventory source</span><strong>Demo InventoryService-shaped read model</strong></div><div><span>Backend API</span><strong>Not connected yet</strong></div><div><span>Realtime</span><strong>Reserved for WebSocket / SSE</strong></div></div></details>
    </div>
  );
}

function PrinterCard({ printer, onOpen, expanded = false }: { printer: PrinterViewModel; onOpen: () => void; expanded?: boolean }) {
  const job = printer.snapshot.activeJob;
  return (
    <article className={`printer-card ${expanded ? 'expanded' : ''}`}>
      <div className="printer-card-head"><div><div className="vendor-label">{printer.identity.vendor}</div><h3>{printer.identity.displayName}</h3><span>{printer.identity.model ?? printer.identity.adapterKind}</span></div><StatusBadge printer={printer} /></div>
      {job ? <div className="job-block"><div className="job-title-row"><strong>{job.name ?? 'Active job'}</strong><span>{formatPercent(job.progress)}</span></div><Progress value={job.progress} /><div className="job-meta"><span>{formatDuration(job.elapsedSeconds)} elapsed</span><span>{formatDuration(job.remainingSeconds)} left</span><span>{job.currentLayer ?? '—'} / {job.totalLayers ?? '—'} layers</span></div></div> : <div className="idle-surface">Idle · ready for the next queue entry</div>}
      <div className="printer-info-strip"><div><span>Connection</span><strong>{printer.snapshot.connection}</strong></div><div><span>Material</span><strong>{describeMaterialSource(printer)}</strong></div><div><span>Updated</span><strong>{formatRelativeTime(printer.snapshot.observedAt).replace('Updated ', '')}</strong></div></div>
      <div className="printer-card-footer"><div className="slot-dots">{slotsFor(printer).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}</div><button className="text-button" onClick={onOpen}>Open printer →</button></div>
    </article>
  );
}

function PrinterDrawer({ fleet, printer, onClose }: { fleet: FleetData; printer: PrinterViewModel; onClose: () => void }) {
  const [tab, setTab] = useState<PrinterTab>('overview');
  const job = printer.snapshot.activeJob;
  const queueCount = fleet.queue.filter((entry) => entry.printerId === printer.identity.printerId).length;
  return (
    <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`${printer.identity.displayName} details`}>
        <div className="drawer-head cockpit-head"><div><div className="eyebrow">{printer.identity.vendor}</div><h2>{printer.identity.displayName}</h2><p>{printer.identity.model ?? 'Unknown model'}</p></div><div className="drawer-head-actions"><StatusBadge printer={printer} /><button className="icon-button" onClick={onClose}>×</button></div></div>
        <div className="printer-tabs">{(['overview', 'materials', 'diagnostics'] as PrinterTab[]).map((item) => <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item[0].toUpperCase() + item.slice(1)}</button>)}</div>
        <div className="drawer-body stack-lg">
          {tab === 'overview' && <><div className="cockpit-meta-line"><span>{formatRelativeTime(printer.snapshot.observedAt)}</span><span>{queueCount} queued</span></div><div className="cockpit-kpi-grid"><CockpitKpi label="Connection" value={printer.snapshot.connection} /><CockpitKpi label="State" value={printerStatusLabel(printer)} /><CockpitKpi label="Material" value={describeMaterialSource(printer)} />{job && <><CockpitKpi label="Progress" value={formatPercent(job.progress)} /><CockpitKpi label="Time left" value={formatDuration(job.remainingSeconds)} /><CockpitKpi label="Layer" value={`${job.currentLayer ?? '—'} / ${job.totalLayers ?? '—'}`} /></>}</div>{job ? <section className="panel inset active-job-card"><div className="active-job-heading"><div><span>Active job</span><strong>{job.name ?? 'Unnamed job'}</strong></div><strong>{formatPercent(job.progress)}</strong></div><Progress value={job.progress} /></section> : <section className="ready-card panel inset"><div className="ready-indicator"><span className="status-dot good" /></div><div><strong>Ready for the next job</strong><span>No active print reported.</span></div></section>}</>}
          {tab === 'materials' && <div className="material-units">{printer.materialSystem?.units.map((unit) => <div className="material-unit drawer-unit" key={unit.unitId}><div className="material-unit-head"><div><strong>{unit.label ?? unit.kind}</strong><span>{friendlyUnit(unit.kind)}</span></div></div><div className="slot-grid">{unit.slots.map((slot) => <MaterialSlot key={slot.slotId} slot={slot} />)}</div></div>) ?? <div className="empty-state">Material information is not available.</div>}</div>}
          {tab === 'diagnostics' && <section className="panel definition-list cockpit-diagnostics"><div><span>Printer ID</span><strong>{printer.identity.printerId}</strong></div><div><span>Adapter</span><strong>{printer.identity.adapterKind}</strong></div><div><span>Observed</span><strong>{printer.snapshot.observedAt}</strong></div>{printer.capabilities.map((capability) => <div key={capability.capabilityId}><span>Capability</span><strong>{capability.capabilityId} · v{capability.majorVersion}</strong></div>)}</section>}
        </div>
      </aside>
    </div>
  );
}

function QueueRow({ fleet, entry, compact = false }: { fleet: FleetData; entry: QueueViewModel; compact?: boolean }) {
  const printer = fleet.printers.find((candidate) => candidate.identity.printerId === entry.printerId);
  if (compact) return <div className="compact-row"><div><strong>{entry.requestedName}</strong><span>{printer?.identity.displayName ?? entry.printerId}</span></div><span className={`queue-badge state-${entry.state}`}>{entry.state}</span></div>;
  return <div className="table-row queue-grid"><div><strong>{entry.requestedName}</strong><span>{entry.filename} · {entry.format.toUpperCase()}</span>{entry.blocker && <small className="warning-text">{entry.blocker}</small>}</div><div><strong>{printer?.identity.displayName ?? entry.printerId}</strong><span>{printer?.identity.adapterKind ?? 'unknown'}</span></div><div><span className={`queue-badge state-${entry.state}`}>{entry.state}</span></div><div><strong>{entry.attemptCount}</strong><span>dispatch attempts</span></div><div><strong>{new Date(entry.updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong><span>{new Date(entry.updatedAt).toLocaleDateString()}</span></div></div>;
}

function MaterialSlot({ slot }: { slot: MaterialSlotSnapshot }) {
  const material = slot.detectedMaterial;
  const fraction = material?.remainingFraction;
  return <div className={`material-slot ${slot.activity === 'active' ? 'active' : ''}`}><div className="material-slot-head"><MaterialDot slot={slot} /><div><strong>{slot.label ?? `Slot ${slot.position + 1}`}</strong><span>{slot.activity === 'active' ? 'Active source' : slot.presence}</span></div></div>{material ? <><div className="material-name">{[material.vendorName, material.productName ?? material.materialFamily].filter(Boolean).join(' ')}</div><div className="material-remaining">{fraction === undefined ? 'Remaining unknown' : `${Math.round(fraction * 100)}% remaining`}</div>{fraction !== undefined && <Progress value={fraction} compact />}</> : <div className="empty-slot-label">Empty</div>}</div>;
}

function MaterialDot({ slot }: { slot: MaterialSlotSnapshot }) {
  const value = slot.detectedMaterial?.rgbaHex;
  const color = value?.length === 9 ? value.slice(0, 7) : value ?? '#475569';
  const low = (slot.detectedMaterial?.remainingFraction ?? 1) <= 0.2;
  return <span className={`material-dot ${slot.activity === 'active' ? 'active' : ''} ${low ? 'low' : ''}`} style={{ background: color }} />;
}

function StatusBadge({ printer }: { printer: PrinterViewModel }) {
  const tone = printerTone(printer);
  return <span className={`status-badge tone-${tone}`}><span className={`status-dot ${tone}`} />{printerStatusLabel(printer)}</span>;
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
  return <div className="page-intro"><div><div className="eyebrow">{eyebrow}</div><h2>{title}</h2><p>{text}</p></div>{action && <button className="primary-button" disabled title="Requires the public API">{action}</button>}</div>;
}

function CockpitKpi({ label, value }: { label: string; value: string }) {
  return <div className="cockpit-kpi"><span>{label}</span><strong>{value}</strong></div>;
}

function slotsFor(printer: PrinterViewModel): MaterialSlotSnapshot[] {
  return printer.materialSystem?.units.flatMap((unit) => unit.slots) ?? [];
}

function friendlyUnit(kind: string): string {
  if (kind === 'multi_slot') return 'Multi-slot';
  if (kind === 'external') return 'External';
  if (kind === 'toolhead') return 'Toolhead';
  return 'Material unit';
}
