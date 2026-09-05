// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { demoModeEnabled } from '../../data/apiClient';
import {
  loadReconnectDiagnostics,
  reconnectDiagnosticForPrinter,
  type ReconnectDiagnostic,
} from './reconnectDiagnosticsClient';

type Copy = {
  title: string;
  subtitle: string;
  loading: string;
  unavailable: string;
  demoUnavailable: string;
  noHistory: string;
  status: string;
  retrying: string;
  recovered: string;
  checking: string;
  recorded: string;
  consecutiveFailures: string;
  lastError: string;
  retryable: string;
  lastFailure: string;
  lastAttempt: string;
  nextRetry: string;
  recoveredAt: string;
  yes: string;
  no: string;
  never: string;
  errors: Record<string, string>;
};

const copy: Record<'en' | 'ru' | 'uk', Copy> = {
  en: {
    title: 'Reconnect history',
    subtitle: 'Sanitized runtime context. Credentials and raw transport errors are never shown here.',
    loading: 'Loading reconnect diagnostics…',
    unavailable: 'Reconnect diagnostics are temporarily unavailable.',
    demoUnavailable: 'Reconnect diagnostics are not queried while demo data is active.',
    noHistory: 'No reconnect incident has been recorded for this printer in the current FoxForge runtime.',
    status: 'Status',
    retrying: 'Retrying connection',
    recovered: 'Recovered',
    checking: 'Reconnect attempt in progress',
    recorded: 'Last incident recorded',
    consecutiveFailures: 'Consecutive failures',
    lastError: 'Last normalized error',
    retryable: 'Adapter marked retryable',
    lastFailure: 'Last failure',
    lastAttempt: 'Last reconnect attempt',
    nextRetry: 'Next retry',
    recoveredAt: 'Recovered at',
    yes: 'Yes',
    no: 'No',
    never: '—',
    errors: {
      connection_unavailable: 'Connection unavailable',
      authentication_failed: 'Authentication failed',
      timeout: 'Connection timeout',
      busy: 'Printer busy',
      not_ready: 'Printer not ready',
      invalid_request: 'Invalid request',
      unsupported: 'Unsupported operation',
      conflict: 'State conflict',
      remote_rejected: 'Printer rejected the request',
      indeterminate: 'Outcome indeterminate',
      internal_adapter_error: 'Internal adapter error',
    },
  },
  ru: {
    title: 'История переподключения',
    subtitle: 'Безопасная диагностика runtime. Учётные данные и исходные ошибки транспорта здесь не отображаются.',
    loading: 'Загрузка диагностики переподключения…',
    unavailable: 'Диагностика переподключения временно недоступна.',
    demoUnavailable: 'При включённых демо-данных диагностика переподключения не запрашивается.',
    noHistory: 'В текущем запуске FoxForge для этого принтера ещё не зарегистрировано проблем переподключения.',
    status: 'Состояние',
    retrying: 'Повторное подключение',
    recovered: 'Связь восстановлена',
    checking: 'Идёт попытка переподключения',
    recorded: 'Последний сбой сохранён',
    consecutiveFailures: 'Ошибок подряд',
    lastError: 'Последняя нормализованная ошибка',
    retryable: 'Адаптер разрешает повтор',
    lastFailure: 'Последний сбой',
    lastAttempt: 'Последняя попытка подключения',
    nextRetry: 'Следующая попытка',
    recoveredAt: 'Связь восстановлена',
    yes: 'Да',
    no: 'Нет',
    never: '—',
    errors: {
      connection_unavailable: 'Принтер недоступен по сети',
      authentication_failed: 'Ошибка авторизации',
      timeout: 'Тайм-аут подключения',
      busy: 'Принтер занят',
      not_ready: 'Принтер не готов',
      invalid_request: 'Некорректный запрос',
      unsupported: 'Операция не поддерживается',
      conflict: 'Конфликт состояния',
      remote_rejected: 'Принтер отклонил запрос',
      indeterminate: 'Результат не определён',
      internal_adapter_error: 'Внутренняя ошибка адаптера',
    },
  },
  uk: {
    title: 'Історія перепідключення',
    subtitle: 'Безпечна діагностика runtime. Облікові дані та сирі помилки транспорту тут не відображаються.',
    loading: 'Завантаження діагностики перепідключення…',
    unavailable: 'Діагностика перепідключення тимчасово недоступна.',
    demoUnavailable: 'Коли ввімкнені демо-дані, діагностика перепідключення не запитується.',
    noHistory: 'У поточному запуску FoxForge для цього принтера ще не зареєстровано проблем перепідключення.',
    status: 'Стан',
    retrying: 'Повторне підключення',
    recovered: 'Зв’язок відновлено',
    checking: 'Триває спроба перепідключення',
    recorded: 'Останній збій збережено',
    consecutiveFailures: 'Помилок поспіль',
    lastError: 'Остання нормалізована помилка',
    retryable: 'Адаптер дозволяє повтор',
    lastFailure: 'Останній збій',
    lastAttempt: 'Остання спроба підключення',
    nextRetry: 'Наступна спроба',
    recoveredAt: 'Зв’язок відновлено',
    yes: 'Так',
    no: 'Ні',
    never: '—',
    errors: {
      connection_unavailable: 'Принтер недоступний у мережі',
      authentication_failed: 'Помилка авторизації',
      timeout: 'Тайм-аут підключення',
      busy: 'Принтер зайнятий',
      not_ready: 'Принтер не готовий',
      invalid_request: 'Некоректний запит',
      unsupported: 'Операція не підтримується',
      conflict: 'Конфлікт стану',
      remote_rejected: 'Принтер відхилив запит',
      indeterminate: 'Результат не визначено',
      internal_adapter_error: 'Внутрішня помилка адаптера',
    },
  },
};

export function ReconnectDiagnosticsPanel({ printerId }: { printerId: string }) {
  const { i18n } = useTranslation();
  const language = (i18n.resolvedLanguage ?? i18n.language).slice(0, 2) as keyof typeof copy;
  const c = copy[language] ?? copy.en;
  const locale = i18n.resolvedLanguage ?? i18n.language;
  const demo = demoModeEnabled();
  const query = useQuery({
    queryKey: ['diagnostics', 'reconnect'],
    queryFn: loadReconnectDiagnostics,
    enabled: !demo,
    placeholderData: [],
    refetchInterval: demo ? false : 5_000,
  });

  const diagnostic = reconnectDiagnosticForPrinter(query.data ?? [], printerId);

  return (
    <section className="panel reconnect-diagnostics-panel">
      <div className="printer-section-heading compact-heading">
        <div><div className="eyebrow">{c.title}</div><h3>{c.title}</h3></div>
      </div>
      <p>{c.subtitle}</p>
      {demo ? (
        <div className="empty-state">{c.demoUnavailable}</div>
      ) : query.isPending ? (
        <div className="empty-state" role="status">{c.loading}</div>
      ) : query.isError ? (
        <div className="runtime-notice error" role="alert"><div><strong>{c.unavailable}</strong></div></div>
      ) : diagnostic ? (
        <ReconnectDefinitionList diagnostic={diagnostic} copy={c} locale={locale} />
      ) : (
        <div className="empty-state">{c.noHistory}</div>
      )}
    </section>
  );
}

function ReconnectDefinitionList({ diagnostic, copy: c, locale }: {
  diagnostic: ReconnectDiagnostic;
  copy: Copy;
  locale: string;
}) {
  const status = diagnostic.consecutiveFailures > 0
    ? c.retrying
    : diagnostic.recoveredAt
      ? c.recovered
      : diagnostic.lastAttemptAt && !diagnostic.lastFailureAt
        ? c.checking
        : c.recorded;

  return (
    <div className="definition-list reconnect-diagnostics-list">
      <div><span>{c.status}</span><strong>{status}</strong></div>
      <div><span>{c.consecutiveFailures}</span><strong>{diagnostic.consecutiveFailures}</strong></div>
      <div><span>{c.lastError}</span><strong>{formatError(diagnostic.lastErrorCode, c)}</strong></div>
      <div><span>{c.retryable}</span><strong>{formatBoolean(diagnostic.lastErrorRetryable, c)}</strong></div>
      <div><span>{c.lastFailure}</span><strong>{formatTimestamp(diagnostic.lastFailureAt, locale, c.never)}</strong></div>
      <div><span>{c.lastAttempt}</span><strong>{formatTimestamp(diagnostic.lastAttemptAt, locale, c.never)}</strong></div>
      {diagnostic.nextRetryAt && <div><span>{c.nextRetry}</span><strong>{formatTimestamp(diagnostic.nextRetryAt, locale, c.never)}</strong></div>}
      {diagnostic.recoveredAt && <div><span>{c.recoveredAt}</span><strong>{formatTimestamp(diagnostic.recoveredAt, locale, c.never)}</strong></div>}
    </div>
  );
}

function formatError(code: string | undefined, c: Copy): string {
  if (!code) return c.never;
  const description = c.errors[code];
  return description ? `${description} · ${code}` : code;
}

function formatBoolean(value: boolean | undefined, c: Copy): string {
  if (value === undefined) return c.never;
  return value ? c.yes : c.no;
}

function formatTimestamp(value: string | undefined, locale: string, fallback: string): string {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(locale, { dateStyle: 'medium', timeStyle: 'medium' });
}
