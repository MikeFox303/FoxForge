// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  authenticatedCommandFetch,
  clearOperatorCommandToken,
  hasOperatorCommandToken,
  setOperatorCommandToken,
} from '../../data/commandClient';

export function OperatorAccess() {
  const { t } = useTranslation();
  const [token, setToken] = useState('');
  const [unlocked, setUnlocked] = useState(() => hasOperatorCommandToken());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const unlock = async () => {
    if (!token.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      setOperatorCommandToken(token);
      const response = await authenticatedCommandFetch('/api/v1/printers/configuration');
      if (!response.ok) {
        const payload = await response.json().catch(() => null) as { error?: { code?: string } } | null;
        clearOperatorCommandToken();
        if (payload?.error?.code === 'command_api_disabled') {
          throw new Error(t('operatorAccess.disabled'));
        }
        throw new Error(t('operatorAccess.invalid'));
      }
      setToken('');
      setUnlocked(true);
      setPanelOpen(false);
    } catch (cause) {
      clearOperatorCommandToken();
      setUnlocked(false);
      setError(cause instanceof Error ? cause.message : t('operatorAccess.invalid'));
    } finally {
      setBusy(false);
    }
  };

  const submitUnlock = (event: FormEvent) => {
    event.preventDefault();
    void unlock();
  };

  const lock = () => {
    clearOperatorCommandToken();
    setToken('');
    setUnlocked(false);
    setPanelOpen(false);
    setError(null);
  };

  return (
    <div className={`operator-access-frame ${panelOpen ? 'is-open' : 'is-collapsed'} ${unlocked ? 'is-unlocked' : ''}`}>
      <button
        className="operator-access-toggle"
        type="button"
        aria-expanded={panelOpen}
        aria-label={`${t('operatorAccess.token')}: ${t(unlocked ? 'operatorAccess.unlocked' : 'operatorAccess.locked')}`}
        onClick={() => setPanelOpen((open) => !open)}
      >
        <span className={`status-dot ${unlocked ? 'good' : ''}`} aria-hidden="true" />
        <span className="operator-access-toggle-label">
          {t(unlocked ? 'operatorAccess.unlocked' : 'operatorAccess.locked')}
        </span>
        <span className="operator-access-toggle-icon" aria-hidden="true">{panelOpen ? '×' : '⌃'}</span>
      </button>

      {unlocked ? (
        <div className="operator-access operator-access-unlocked" role="status">
          <span className="operator-access-unlocked-label">{t('operatorAccess.unlocked')}</span>
          {panelOpen && <small>{t('operatorAccess.memoryHelp')}</small>}
          <button className="text-button" type="button" onClick={lock}>{t('operatorAccess.lock')}</button>
        </div>
      ) : (
        <form className="operator-access" onSubmit={submitUnlock}>
          <div className="operator-access-help">
            <small>{t('operatorAccess.credentialHelp')}</small>
            <small>{t('operatorAccess.memoryHelp')}</small>
          </div>
          <label>
            <span className="sr-only">{t('operatorAccess.token')}</span>
            <input
              type="password"
              autoComplete="off"
              value={token}
              placeholder={t('operatorAccess.placeholder')}
              onChange={(event) => setToken(event.currentTarget.value)}
            />
          </label>
          <button className="text-button" type="submit" disabled={!token.trim() || busy}>
            {busy ? t('operatorAccess.checking') : t('operatorAccess.unlock')}
          </button>
          {error && <small className="warning-text" role="alert">{error}</small>}
        </form>
      )}
    </div>
  );
}
