// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { CommandApiError } from '../../data/commandClient';
import type { PrinterSetupOutcome } from '../../data/printerSetupClient';

export type SetupLanguage = 'en' | 'ru' | 'uk';

type ConnectionError = NonNullable<PrinterSetupOutcome['connectionError']>;

type SetupErrorCopy = {
  unavailable: string;
  authentication: string;
  timeout: string;
  initialState: string;
  internal: string;
};

const messages: Record<SetupLanguage, SetupErrorCopy> = {
  en: {
    unavailable: 'FoxForge cannot reach the printer. Check its IP/hostname, power, and LAN access from the server.',
    authentication: 'The printer rejected the LAN access code. Check the code and the printer LAN/Developer mode settings.',
    timeout: 'The Bambu MQTT connection did not complete in time. Check the network and TCP port 8883.',
    initialState: 'MQTT connected, but no printer state arrived. Check the Bambu serial number and LAN mode.',
    internal: 'FoxForge hit an internal adapter error while connecting. The printer was not saved; retry or open Diagnostics.',
  },
  ru: {
    unavailable: 'FoxForge не может подключиться к принтеру. Проверьте IP/имя хоста, питание и доступ к локальной сети с сервера.',
    authentication: 'Принтер отклонил LAN access code. Проверьте код доступа и настройки LAN/Developer mode на принтере.',
    timeout: 'Подключение к Bambu MQTT не завершилось вовремя. Проверьте сеть и доступность TCP-порта 8883.',
    initialState: 'MQTT-соединение установлено, но состояние принтера не получено. Проверьте серийный номер Bambu и LAN mode.',
    internal: 'Внутренняя ошибка адаптера при подключении. Принтер не сохранён; повторите попытку или откройте диагностику.',
  },
  uk: {
    unavailable: 'FoxForge не може підключитися до принтера. Перевірте IP/ім’я хоста, живлення та доступ до локальної мережі із сервера.',
    authentication: 'Принтер відхилив LAN access code. Перевірте код доступу та налаштування LAN/Developer mode на принтері.',
    timeout: 'Підключення до Bambu MQTT не завершилося вчасно. Перевірте мережу та доступність TCP-порту 8883.',
    initialState: 'MQTT-з’єднання встановлено, але стан принтера не отримано. Перевірте серійний номер Bambu та LAN mode.',
    internal: 'Внутрішня помилка адаптера під час підключення. Принтер не збережено; повторіть спробу або відкрийте діагностику.',
  },
};

export function setupCommandErrorMessage(cause: unknown, language: SetupLanguage): string | null {
  if (!(cause instanceof CommandApiError)) return null;
  const copy = messages[language];
  switch (cause.code) {
    case 'printer_connection_unavailable':
      return copy.unavailable;
    case 'printer_connection_authentication_failed':
      return copy.authentication;
    case 'printer_connection_timeout':
      return copy.timeout;
    case 'printer_initial_state_timeout':
      return copy.initialState;
    case 'printer_connection_internal_adapter_error':
      return copy.internal;
    default:
      return null;
  }
}

export function setupOutcomeErrorMessage(error: ConnectionError, language: SetupLanguage): string {
  const copy = messages[language];
  if (error.vendorCode === 'initial_state_timeout') return copy.initialState;
  switch (error.code) {
    case 'connection_unavailable':
      return copy.unavailable;
    case 'authentication_failed':
      return copy.authentication;
    case 'timeout':
      return copy.timeout;
    case 'internal_adapter_error':
      return copy.internal;
    default:
      return error.message;
  }
}
