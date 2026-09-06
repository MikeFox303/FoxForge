// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, useLocation } from 'react-router-dom';

import { fleetRuntimeTone, type FleetRuntimeState } from '../data/fleetGateway';
import { PrinterSetupLauncher } from '../features/printers/PrinterSetupLauncher';
import { OperatorAccess } from '../features/security/OperatorAccess';
import { activeNavigationItem, navigation } from './navigation';

export function AppShell({ runtime, children }: { runtime: FleetRuntimeState; children: ReactNode }) {
  const location = useLocation();
  const { t } = useTranslation();
  const current = activeNavigationItem(location.pathname);
  const runtimeTone = fleetRuntimeTone(runtime.phase);
  const runtimeLabel = runtime.isRefreshing ? t('alpha.runtime.refreshing') : t(`alpha.runtime.${runtime.phase}`);

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
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              <span>{t(`nav.${item.key}`)}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="runtime-status">
            <span className={`status-dot ${runtimeTone}`} />
            <div>
              <strong>{t('alpha.shell.build')}</strong>
              <span>{runtimeLabel}</span>
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
            <div className={`live-pill tone-${runtimeTone}`} aria-live="polite">
              <span className={`status-dot ${runtimeTone}`} /> {runtimeLabel}
            </div>
            <PrinterSetupLauncher />
            <div className="operator-access-shell">
              <OperatorAccess />
            </div>
          </div>
        </header>

        <div className="content">{children}</div>
      </main>
    </div>
  );
}
