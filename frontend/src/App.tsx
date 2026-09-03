// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import { useFleetData } from './data/fleetGateway';
import type { FleetData, MaterialSlotSnapshot, PrinterViewModel, QueueViewModel } from './domain';
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

type ViewId = 'overview' | 'printers' | 'queue' | 'materials' | 'farm' | 'system';
type PrinterTab = 'overview' | 'materials' | 'diagnostics';
type TranslationKey = 'nav.overview' | 'nav.printers' | 'nav.queue' | 'nav.materials' | 'nav.farm' | 'nav.system';

const navigation: Array<{ id: ViewId; labelKey: TranslationKey; short: string; path: string }> = [
  { id: 'overview', labelKey: 'nav.overview', short: 'OV', path: '/' },
  { id: 'printers', labelKey: 'nav.printers', short: 'PR', path: '/printers' },
  { id: 'queue', labelKey: 'nav.queue', short: 'QU', path: '/queue' },
  { id: 'materials', labelKey: 'nav.materials', short: 'MT', path: '/materials' },
  { id: 'farm', labelKey: 'nav.farm', short: 'FM', path: '/farm' },
  { id: 'system', labelKey: 'nav.system', short: 'SY', path: '/system' },
];

export function App() {
  const data = useFleetData();
  const [selectedPrinterId, setSelectedPrinterId] = useState<string | null>(null);
  const summary = useMemo(() => summarizeFleet(data), [data]);
  const selectedPrinter = selectedPrinterId ? findPrinter(data, selectedPrinterId) : undefined;
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  const currentNavigation = navigation.find((item) => item.path === location.pathname) ?? navigation[0];

  const navigateToView = (view: ViewId) => {
    const item = navigation.find((candidate) => candidate.id === view);
    if (item) navigate(item.path);
  };

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
            <NavLink
              key={item.id}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon" aria-hidden="true">{item.short}</span>
              <span>{t(item.labelKey)}</span>
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
          <a
            className="support-link"
            href="https://ko-fi.com/mikefox303"
            target="_blank"
            rel="noreferrer"
            aria-label={`${t('shell.support')} (opens in a new tab)`}
          >
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
            <h1>{t(currentNavigation.labelKey)}</h1>
          </div>
          <div className="topbar-actions">
            <div className="live-pill"><span className="status-dot good" /> {t('shell.preview')}</div>
            <button className="secondary-button" disabled title="Printer setup will be enabled with the public API">{t('shell.addPrinter')}</button>
          </div>
        </header>

        <div className="content">
          <Routes>
            <Route
              path="/"
              element={(
                <OverviewView
                  data={data}
                  summary={summary}
                  onOpenPrinter={(printerId) => setSelectedPrinterId(printerId)}
                  onNavigate={navigateToView}
                />
              )}
            />
            <Route path="/printers" element={<PrintersView data={data} onOpenPrinter={(printerId) => setSelectedPrinterId(printerId)} />} />
            <Route path="/queue" element={<QueueView data={data} />} />
            <Route path="/materials" element={<MaterialsView data={data} />} />
            <Route path="/farm" element={<FarmView data={data} onOpenPrinter={(printerId) => setSelectedPrinterId(printerId)} />} />
            <Route path="/system" element={<SystemView />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>

      {selectedPrinter && <PrinterDrawer data={data} printer={selectedPrinter} onClose={() => setSelectedPrinterId(null)} />}
    </div>
  );
}

function OverviewView({
  data,
  summary,
  onOpenPrinter,
  onNavigate,
}: {
  data: FleetData;
  summary: ReturnType<typeof summarizeFleet>;
  onOpenPrinter: (printerId: string) => void;
  onNavigate: (view: ViewId) => void;
}) {
  return (
    <div className="stack-xl">
      <section className="hero-panel">
        <div>
          <div className="eyebrow accent">Mixed fleet, one workspace</div>
          <h2>Your printers, jobs and materials in one place.</h2>
          <p>
            FoxForge keeps everyday fleet workflows consistent while allowing each printer family to expose its deeper features when they are available.
          </p>
        </div>
        <div className="hero-actions">
          <button className="primary-button" onClick={() => onNavigate('printers')}>Open fleet</button>
          <button className="secondary-button" onClick={() => onNavigate('queue')}>View queue</button>
        </div>
      </section>

      <section className="metric-grid" aria-label="Fleet summary">
        <Metric label="Printers" value={String(summary.totalPrinters)} detail={`${summary.connectedPrinters} connected`} />
        <Metric label="Printing now" value={String(summary.printingPrinters)} detail="Across the fleet" />
        <Metric label="Waiting / blocked" value={String(summary.queuedJobs)} detail="Jobs needing attention or a turn" />
        <Metric
          label="Material alerts"
          value={String(summary.materialAlerts)}
          detail="Loaded slots at or below 20%"
          tone={summary.materialAlerts > 0 ? 'warning' : 'good'}
        />
      </section>

      <SectionHeader title="Fleet" subtitle="Current status, active jobs and loaded materials." actionLabel="All printers" onAction={() => onNavigate('printers')} />
      <div className="printer-grid">
        {data.printers.map((printer) => (
          <PrinterCard key={printer.identity.printerId} printer={printer} onOpen={() => onOpenPrinter(printer.identity.printerId)} />
        ))}
      </div>

      <div className="two-column">
        <section className="panel">
          <SectionHeader title="Queue pulse" subtitle="What is running, waiting or blocked right now." actionLabel="Open queue" onAction={() => onNavigate('queue')} />
          <div className="compact-list">
            {data.queue.map((entry) => <QueueRow data={data} key={entry.queueId} entry={entry} compact />)}
          </div>
        </section>
        <section className="panel">
          <SectionHeader title="Material systems" subtitle="Loaded filament across multi-slot systems and external spools." actionLabel="Open materials" onAction={() => onNavigate('materials')} />
          <div className="compact-list">
            {data.printers.map((printer) => (
              <div className="material-summary" key={printer.identity.printerId}>
                <div>
                  <strong>{printer.identity.displayName}</strong>
                  <span>{materialSystemLabel(printer)}</span>
                </div>
                <div className="slot-dots" aria-label="Material slots">
                  {printer.materialSystem?.units.flatMap((unit) => unit.slots).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function PrintersView({ data, onOpenPrinter }: { data: FleetData; onOpenPrinter: (printerId: string) => void }) {
  return (
    <div className="stack-lg">
      <SectionHeader title="Printers" subtitle="Status, current jobs and loaded materials across the fleet." />
      <div className="printer-grid">
        {data.printers.map((printer) => (
          <PrinterCard key={printer.identity.printerId} printer={printer} onOpen={() => onOpenPrinter(printer.identity.printerId)} expanded />
        ))}
      </div>
    </div>
  );
}

function QueueView({ data }: { data: FleetData }) {
  return (
    <div className="stack-lg">
      <div className="page-intro">
        <div>
          <div className="eyebrow">Safe print scheduling</div>
          <h2>Print queue</h2>
          <p>Follow every job from waiting through printer acceptance without hiding blocked or uncertain starts.</p>
        </div>
        <button className="primary-button" disabled title="Requires the public API">Add job</button>
      </div>
      <section className="panel table-panel">
        <div className="table-head queue-grid">
          <span>Job</span><span>Printer</span><span>State</span><span>Attempts</span><span>Updated</span>
        </div>
        {data.queue.map((entry) => <QueueRow data={data} key={entry.queueId} entry={entry} />)}
      </section>
      <section className="callout warning">
        <strong>Uncertain starts stay visible</strong>
        <span>
          If FoxForge cannot prove whether a printer received a start command, the job remains indeterminate instead of being silently started again.
        </span>
      </section>
    </div>
  );
}

function MaterialsView({ data }: { data: FleetData }) {
  return (
    <div className="stack-lg">
      <div className="page-intro">
        <div>
          <div className="eyebrow">Filament & material systems</div>
          <h2>Materials</h2>
          <p>See what is loaded, which source is active and which spools are getting low.</p>
        </div>
      </div>
      {data.printers.map((printer) => (
        <section className="panel" key={printer.identity.printerId}>
          <SectionHeader title={printer.identity.displayName} subtitle={`${printer.identity.vendor} ${printer.identity.model ?? ''}`} />
          {!printer.materialSystem ? (
            <div className="empty-state">Material information is not available for this printer yet.</div>
          ) : (
            <div className="material-units">
              {printer.materialSystem.units.map((unit) => (
                <div className="material-unit" key={unit.unitId}>
                  <div className="material-unit-head">
                    <div>
                      <strong>{unit.label ?? friendlyMaterialUnitKind(unit.kind)}</strong>
                      <span>{friendlyMaterialUnitKind(unit.kind)}</span>
                    </div>
                    <span className="count-pill">{unit.slots.length} slot{unit.slots.length === 1 ? '' : 's'}</span>
                  </div>
                  <div className="slot-grid">
                    {unit.slots.map((slot) => <MaterialSlot key={slot.slotId} slot={slot} />)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      ))}
    </div>
  );
}

function FarmView({ data, onOpenPrinter }: { data: FleetData; onOpenPrinter: (printerId: string) => void }) {
  const summary = summarizeFleet(data);
  const utilization = summary.totalPrinters === 0 ? 0 : Math.round((summary.printingPrinters / summary.totalPrinters) * 100);

  return (
    <div className="stack-lg">
      <section className="farm-hero">
        <div>
          <div className="eyebrow accent">Farm command center</div>
          <h2>{summary.printingPrinters} active · {summary.connectedPrinters}/{summary.totalPrinters} connected</h2>
          <p>A denser operational view for watching multiple printers and the next jobs at a glance.</p>
        </div>
        <div className="farm-utilization">
          <span>Current utilization</span>
          <strong>{utilization}%</strong>
        </div>
      </section>

      <div className="farm-grid">
        {data.printers.map((printer) => {
          const queued = queueCountForPrinter(data, printer.identity.printerId);
          return (
            <article className="farm-tile" key={printer.identity.printerId}>
              <div className="farm-tile-head">
                <div>
                  <strong>{printer.identity.displayName}</strong>
                  <span>{printer.identity.vendor} · {printer.identity.model}</span>
                </div>
                <StatusBadge printer={printer} />
              </div>
              <div className="farm-info-row">
                <span>{describeMaterialSource(printer)}</span>
                <span>{queued} queued</span>
              </div>
              {printer.snapshot.activeJob ? (
                <>
                  <div className="farm-job">{printer.snapshot.activeJob.name}</div>
                  <Progress value={printer.snapshot.activeJob.progress} />
                  <div className="farm-job-meta">
                    <span>{formatPercent(printer.snapshot.activeJob.progress)}</span>
                    <span>{formatDuration(printer.snapshot.activeJob.remainingSeconds)} left</span>
                  </div>
                </>
              ) : <div className="idle-surface">Ready for the next job</div>}
              <div className="farm-tile-footer">
                <div className="slot-dots">
                  {printer.materialSystem?.units.flatMap((unit) => unit.slots).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}
                </div>
                <button className="text-button" onClick={() => onOpenPrinter(printer.identity.printerId)}>Open printer →</button>
              </div>
            </article>
          );
        })}
      </div>

      <div className="two-column farm-lower-grid">
        <section className="panel">
          <SectionHeader title="Upcoming jobs" subtitle="The next work waiting across the farm." />
          <div className="compact-list">
            {data.queue.map((entry) => <QueueRow data={data} key={entry.queueId} entry={entry} compact />)}
          </div>
        </section>
        <section className="panel">
          <SectionHeader title="Material readiness" subtitle="Quick view of loaded sources before the next dispatch." />
          <div className="compact-list">
            {data.printers.map((printer) => (
              <div className="material-summary" key={printer.identity.printerId}>
                <div>
                  <strong>{printer.identity.displayName}</strong>
                  <span>{describeMaterialSource(printer)}</span>
                </div>
                <div className="slot-dots">
                  {printer.materialSystem?.units.flatMap((unit) => unit.slots).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function SystemView() {
  const { i18n, t } = useTranslation();
  const activeLanguage = i18n.resolvedLanguage ?? i18n.language;

  return (
    <div className="stack-lg">
      <div className="page-intro">
        <div>
          <div className="eyebrow">Application status</div>
          <h2>System</h2>
          <p>Runtime, deployment and interface preferences without mixing technical details into everyday printer screens.</p>
        </div>
      </div>

      <div className="system-card-grid">
        <section className="panel system-card">
          <span className="system-card-label">Runtime</span>
          <strong>Development preview</strong>
          <p>The interface is running with representative demo data while the public server API is being built.</p>
          <div className="system-status-line"><span className="status-dot good" /> UI running</div>
        </section>
        <section className="panel system-card">
          <span className="system-card-label">Deployment target</span>
          <strong>Self-hosted</strong>
          <p>Static frontend assets are intended to ship with the FoxForge server for Docker, ARM64 and Umbrel.</p>
          <div className="system-status-line">Docker · ARM64 · Umbrel</div>
        </section>
        <section className="panel system-card language-card">
          <span className="system-card-label">{t('language.title')}</span>
          <strong>{activeLanguage === 'ru' ? t('language.russian') : activeLanguage === 'uk' ? t('language.ukrainian') : t('language.english')}</strong>
          <p>The localization foundation is active. Current translation coverage starts with the application shell and will expand screen-by-screen.</p>
          <div className="language-switcher" aria-label={t('language.title')}>
            {(['en', 'ru', 'uk'] as const).map((language) => (
              <button
                key={language}
                className={activeLanguage === language ? 'active' : ''}
                onClick={() => void changeInterfaceLanguage(language)}
              >
                {language.toUpperCase()}
              </button>
            ))}
          </div>
        </section>
      </div>

      <details className="diagnostics-panel panel">
        <summary>Developer diagnostics</summary>
        <div className="definition-list diagnostics-list">
          <div><span>Frontend</span><strong>React + TypeScript + Vite</strong></div>
          <div><span>Routing</span><strong>React Router</strong></div>
          <div><span>Server state</span><strong>TanStack Query</strong></div>
          <div><span>Localization</span><strong>i18next · en / ru / uk</strong></div>
          <div><span>Data source</span><strong>Demo gateway</strong></div>
          <div><span>Backend API</span><strong>Not connected yet</strong></div>
          <div><span>Realtime</span><strong>Reserved for WebSocket / SSE</strong></div>
          <div><span>UI boundary</span><strong>Normalized contracts only</strong></div>
        </div>
      </details>
    </div>
  );
}

function PrinterCard({ printer, onOpen, expanded = false }: { printer: PrinterViewModel; onOpen: () => void; expanded?: boolean }) {
  const job = printer.snapshot.activeJob;
  return (
    <article className={`printer-card ${expanded ? 'expanded' : ''}`}>
      <div className="printer-card-head">
        <div>
          <div className="vendor-label">{printer.identity.vendor}</div>
          <h3>{printer.identity.displayName}</h3>
          <span>{printer.identity.model ?? printer.identity.adapterKind}</span>
        </div>
        <StatusBadge printer={printer} />
      </div>

      {job ? (
        <div className="job-block">
          <div className="job-title-row"><strong>{job.name ?? 'Active job'}</strong><span>{formatPercent(job.progress)}</span></div>
          <Progress value={job.progress} />
          <div className="job-meta">
            <span>{formatDuration(job.elapsedSeconds)} elapsed</span>
            <span>{formatDuration(job.remainingSeconds)} left</span>
            <span>{job.currentLayer ?? '—'} / {job.totalLayers ?? '—'} layers</span>
          </div>
        </div>
      ) : (
        <div className="idle-surface">Idle · ready for the next queue entry</div>
      )}

      <div className="printer-info-strip">
        <div><span>Connection</span><strong>{friendlyConnection(printer.snapshot.connection)}</strong></div>
        <div><span>Material</span><strong>{describeMaterialSource(printer)}</strong></div>
        <div><span>Updated</span><strong>{formatRelativeTime(printer.snapshot.observedAt).replace('Updated ', '')}</strong></div>
      </div>

      <div className="printer-card-footer">
        <div className="slot-dots">
          {printer.materialSystem?.units.flatMap((unit) => unit.slots).map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}
        </div>
        <button className="text-button" onClick={onOpen}>Open printer →</button>
      </div>
    </article>
  );
}

function PrinterDrawer({ data, printer, onClose }: { data: FleetData; printer: PrinterViewModel; onClose: () => void }) {
  const [tab, setTab] = useState<PrinterTab>('overview');
  const job = printer.snapshot.activeJob;
  const queued = queueCountForPrinter(data, printer.identity.printerId);

  return (
    <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`${printer.identity.displayName} details`}>
        <div className="drawer-head cockpit-head">
          <div>
            <div className="eyebrow">{printer.identity.vendor}</div>
            <h2>{printer.identity.displayName}</h2>
            <p>{printer.identity.model ?? 'Unknown model'}</p>
          </div>
          <div className="drawer-head-actions">
            <StatusBadge printer={printer} />
            <button className="icon-button" onClick={onClose} aria-label="Close printer details">×</button>
          </div>
        </div>

        <div className="printer-tabs" role="tablist" aria-label="Printer details sections">
          {(['overview', 'materials', 'diagnostics'] as PrinterTab[]).map((item) => (
            <button
              key={item}
              className={tab === item ? 'active' : ''}
              onClick={() => setTab(item)}
              role="tab"
              aria-selected={tab === item}
            >
              {item === 'overview' ? 'Overview' : item === 'materials' ? 'Materials' : 'Diagnostics'}
            </button>
          ))}
        </div>

        <div className="drawer-body stack-lg">
          {tab === 'overview' && (
            <>
              <section className="cockpit-meta-line">
                <span>{formatRelativeTime(printer.snapshot.observedAt)}</span>
                <span>{queued} queued</span>
              </section>

              <section className="cockpit-kpi-grid">
                <CockpitKpi label="Connection" value={friendlyConnection(printer.snapshot.connection)} />
                <CockpitKpi label="State" value={printerStatusLabel(printer)} />
                {job ? (
                  <>
                    <CockpitKpi label="Progress" value={formatPercent(job.progress)} />
                    <CockpitKpi label="Time left" value={formatDuration(job.remainingSeconds)} />
                    <CockpitKpi label="Layer" value={`${job.currentLayer ?? '—'} / ${job.totalLayers ?? '—'}`} />
                    <CockpitKpi label="Material" value={describeMaterialSource(printer)} />
                  </>
                ) : (
                  <>
                    <CockpitKpi label="Material" value={describeMaterialSource(printer)} />
                    <CockpitKpi label="Queue" value={queued === 0 ? 'Clear' : `${queued} waiting`} />
                  </>
                )}
              </section>

              {job ? (
                <section className="panel inset active-job-card">
                  <div className="active-job-heading">
                    <div>
                      <span>Active job</span>
                      <strong>{job.name ?? 'Unnamed job'}</strong>
                    </div>
                    <strong>{formatPercent(job.progress)}</strong>
                  </div>
                  <Progress value={job.progress} />
                  <div className="job-meta drawer-meta">
                    <span>{formatDuration(job.elapsedSeconds)} elapsed</span>
                    <span>{formatDuration(job.remainingSeconds)} left</span>
                    <span>Layer {job.currentLayer ?? '—'} of {job.totalLayers ?? '—'}</span>
                  </div>
                </section>
              ) : (
                <section className="ready-card panel inset">
                  <div className="ready-indicator"><span className="status-dot good" /></div>
                  <div><strong>Ready for the next job</strong><span>No active print is reported by this printer.</span></div>
                </section>
              )}

              <section className="panel inset">
                <SectionHeader title="Loaded materials" subtitle={materialSystemLabel(printer)} />
                {printer.materialSystem ? (
                  <div className="material-overview-list">
                    {printer.materialSystem.units.map((unit) => (
                      <div className="material-overview-row" key={unit.unitId}>
                        <div>
                          <strong>{unit.label ?? friendlyMaterialUnitKind(unit.kind)}</strong>
                          <span>{describeMaterialSourceFromSlots(unit.slots)}</span>
                        </div>
                        <div className="slot-dots">
                          {unit.slots.map((slot) => <MaterialDot key={slot.slotId} slot={slot} />)}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <div className="empty-state">Material information is not available.</div>}
              </section>

              {printer.snapshot.faultSummary.length > 0 && (
                <section className="callout warning">
                  <strong>Printer attention</strong>
                  <span>{printer.snapshot.faultSummary.map((fault) => fault.message ?? fault.code).join(' · ')}</span>
                </section>
              )}
            </>
          )}

          {tab === 'materials' && (
            <section>
              <div className="drawer-section-heading">
                <div><span className="eyebrow">Loaded filament</span><h3>Material system</h3></div>
                <span>{materialSystemLabel(printer)}</span>
              </div>
              {printer.materialSystem?.units.map((unit) => (
                <div className="material-unit drawer-unit" key={unit.unitId}>
                  <div className="material-unit-head">
                    <div><strong>{unit.label ?? friendlyMaterialUnitKind(unit.kind)}</strong><span>{friendlyMaterialUnitKind(unit.kind)}</span></div>
                    <span className="count-pill">{unit.slots.length} slot{unit.slots.length === 1 ? '' : 's'}</span>
                  </div>
                  <div className="slot-grid">{unit.slots.map((slot) => <MaterialSlot key={slot.slotId} slot={slot} compact />)}</div>
                </div>
              )) ?? <div className="empty-state">Material information is not available for this printer.</div>}
            </section>
          )}

          {tab === 'diagnostics' && (
            <>
              <section className="panel definition-list cockpit-diagnostics">
                <div><span>Printer ID</span><strong>{printer.identity.printerId}</strong></div>
                <div><span>Vendor</span><strong>{printer.identity.vendor}</strong></div>
                <div><span>Model</span><strong>{printer.identity.model ?? 'Unknown'}</strong></div>
                <div><span>Adapter</span><strong>{printer.identity.adapterKind}</strong></div>
                <div><span>Connection</span><strong>{printer.snapshot.connection}</strong></div>
                <div><span>Observed at</span><strong>{new Date(printer.snapshot.observedAt).toLocaleString()}</strong></div>
                <div><span>Snapshot stale</span><strong>{printer.snapshot.stale ? 'Yes' : 'No'}</strong></div>
              </section>
              <section>
                <div className="mini-heading">Advertised capabilities</div>
                <div className="capability-row">
                  {printer.capabilities.map((capability) => (
                    <span className="capability-pill" key={capability.capabilityId}>{capability.capabilityId} · v{capability.majorVersion}</span>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

function QueueRow({ data, entry, compact = false }: { data: FleetData; entry: QueueViewModel; compact?: boolean }) {
  const printer = findPrinter(data, entry.printerId);
  if (compact) {
    return (
      <div className="compact-row">
        <div><strong>{entry.requestedName}</strong><span>{printer?.identity.displayName ?? entry.printerId}</span></div>
        <span className={`queue-badge state-${entry.state}`}>{entry.state}</span>
      </div>
    );
  }

  return (
    <div className="table-row queue-grid">
      <div><strong>{entry.requestedName}</strong><span>{entry.filename} · {entry.format.toUpperCase()}</span>{entry.blocker && <small>{entry.blocker}</small>}</div>
      <div><strong>{printer?.identity.displayName ?? entry.printerId}</strong><span>{printer?.identity.vendor ?? 'Unknown vendor'}</span></div>
      <div><span className={`queue-badge state-${entry.state}`}>{entry.state}</span></div>
      <div><strong>{entry.attemptCount}</strong><span>dispatch attempts</span></div>
      <div><strong>{new Date(entry.updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong><span>{new Date(entry.updatedAt).toLocaleDateString()}</span></div>
    </div>
  );
}

function MaterialSlot({ slot, compact = false }: { slot: MaterialSlotSnapshot; compact?: boolean }) {
  const material = slot.detectedMaterial;
  const remaining = material?.remainingFraction;
  const low = remaining !== undefined && remaining <= 0.2;
  return (
    <div className={`material-slot ${slot.activity === 'active' ? 'active' : ''} ${compact ? 'compact' : ''}`}>
      <div className="material-slot-head">
        <span className="spool-color" style={{ background: material?.rgbaHex?.slice(0, 7) ?? 'transparent' }} />
        <div><strong>{slot.label ?? `Slot ${slot.position + 1}`}</strong><span>{slot.activity === 'active' ? 'Active source' : slot.presence}</span></div>
      </div>
      {material ? (
        <>
          <div className="material-name">{material.vendorName ?? 'Unknown'} {material.productName ?? material.materialFamily ?? 'material'}</div>
          <div className="material-remaining"><span>{formatPercent(remaining)} remaining</span>{low && <strong>Low</strong>}</div>
          <Progress value={remaining} compact />
        </>
      ) : <div className="empty-slot">Empty</div>}
    </div>
  );
}

function MaterialDot({ slot }: { slot: MaterialSlotSnapshot }) {
  const remaining = slot.detectedMaterial?.remainingFraction;
  const title = slot.detectedMaterial
    ? `${slot.label ?? slot.slotId}: ${slot.detectedMaterial.materialFamily ?? 'material'} ${formatPercent(remaining)}`
    : `${slot.label ?? slot.slotId}: empty`;
  return (
    <span
      className={`material-dot ${slot.activity === 'active' ? 'active' : ''} ${remaining !== undefined && remaining <= 0.2 ? 'low' : ''}`}
      style={{ background: slot.detectedMaterial?.rgbaHex?.slice(0, 7) ?? 'transparent' }}
      title={title}
    />
  );
}

function StatusBadge({ printer }: { printer: PrinterViewModel }) {
  return <span className={`status-badge tone-${printerTone(printer)}`}><span className={`status-dot ${printerTone(printer)}`} />{printerStatusLabel(printer)}</span>;
}

function Progress({ value, compact = false }: { value?: number; compact?: boolean }) {
  const normalized = Math.min(1, Math.max(0, value ?? 0));
  return (
    <div className={`progress-track ${compact ? 'compact' : ''}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(normalized * 100)}>
      <div className="progress-value" style={{ width: `${normalized * 100}%` }} />
    </div>
  );
}

function Metric({ label, value, detail, tone = 'neutral' }: { label: string; value: string; detail: string; tone?: 'neutral' | 'good' | 'warning' }) {
  return <article className={`metric-card tone-${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function CockpitKpi({ label, value }: { label: string; value: string }) {
  return <div className="cockpit-kpi"><span>{label}</span><strong>{value}</strong></div>;
}

function SectionHeader({ title, subtitle, actionLabel, onAction }: { title: string; subtitle?: string; actionLabel?: string; onAction?: () => void }) {
  return (
    <div className="section-header">
      <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
      {actionLabel && onAction && <button className="text-button" onClick={onAction}>{actionLabel} →</button>}
    </div>
  );
}

function friendlyConnection(connection: PrinterViewModel['snapshot']['connection']): string {
  switch (connection) {
    case 'connected': return 'Connected';
    case 'connecting': return 'Connecting';
    case 'degraded': return 'Degraded';
    case 'disconnected': return 'Disconnected';
  }
}

function friendlyMaterialUnitKind(kind: string): string {
  switch (kind) {
    case 'multi_slot': return 'Multi-slot';
    case 'external': return 'External spool';
    case 'toolhead': return 'Toolhead';
    default: return 'Material unit';
  }
}

function materialSystemLabel(printer: PrinterViewModel): string {
  const units = printer.materialSystem?.units ?? [];
  if (units.length === 0) return 'No material system reported';
  return units.map((unit) => unit.label ?? friendlyMaterialUnitKind(unit.kind)).join(' · ');
}

function describeMaterialSourceFromSlots(slots: MaterialSlotSnapshot[]): string {
  const active = slots.find((slot) => slot.activity === 'active' && slot.detectedMaterial);
  const loaded = slots.find((slot) => slot.presence === 'loaded' && slot.detectedMaterial);
  const selected = active ?? loaded;
  if (!selected?.detectedMaterial) return 'No material loaded';
  const material = selected.detectedMaterial;
  return [material.materialFamily, material.vendorName].filter(Boolean).join(' · ') || 'Material loaded';
}

function queueCountForPrinter(data: FleetData, printerId: string): number {
  return data.queue.filter((entry) => entry.printerId === printerId && ['pending', 'blocked', 'dispatching'].includes(entry.state)).length;
}
