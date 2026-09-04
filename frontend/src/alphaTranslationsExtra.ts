// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import i18n from './i18n';

const extras = {
  en: {
    alpha: {
      shell: {
        fleetControl: 'Fleet control',
        primaryNavigation: 'Primary navigation',
        unavailableAlpha: 'This action is not available in the read-only alpha API yet.',
      },
      status: {
        pending: 'Pending',
        blocked: 'Blocked',
        dispatching: 'Dispatching',
        accepted: 'Accepted',
        cancelled: 'Cancelled',
        indeterminate: 'Indeterminate',
        loaded: 'Loaded',
        empty: 'Empty',
        active: 'Active',
        inactive: 'Inactive',
      },
      runtime: {
        loading: 'Connecting', ready: 'Live API', error: 'API unavailable', refreshing: 'Refreshing',
        loadingTitle: 'Connecting to FoxForge', loadingText: 'Loading the latest fleet and queue snapshot.',
        errorTitle: 'Live data is temporarily unavailable', errorText: 'The interface is still running. Check the server connection or try again.', retry: 'Try again',
      },
    },
  },
  ru: {
    alpha: {
      shell: {
        fleetControl: 'Управление фермой',
        primaryNavigation: 'Основная навигация',
        unavailableAlpha: 'Это действие пока недоступно в read-only alpha API.',
      },
      status: {
        pending: 'Ожидание',
        blocked: 'Заблокировано',
        dispatching: 'Запуск',
        accepted: 'Принято',
        cancelled: 'Отменено',
        indeterminate: 'Неопределённо',
        loaded: 'Загружено',
        empty: 'Пусто',
        active: 'Активно',
        inactive: 'Неактивно',
      },
      runtime: {
        loading: 'Подключение', ready: 'Живой API', error: 'API недоступен', refreshing: 'Обновление',
        loadingTitle: 'Подключение к FoxForge', loadingText: 'Загружаем актуальное состояние принтеров и очереди.',
        errorTitle: 'Живые данные временно недоступны', errorText: 'Интерфейс продолжает работать. Проверьте связь с сервером или повторите попытку.', retry: 'Повторить',
      },
    },
  },
  uk: {
    alpha: {
      shell: {
        fleetControl: 'Керування фермою',
        primaryNavigation: 'Основна навігація',
        unavailableAlpha: 'Ця дія поки недоступна в read-only alpha API.',
      },
      status: {
        pending: 'Очікування',
        blocked: 'Заблоковано',
        dispatching: 'Запуск',
        accepted: 'Прийнято',
        cancelled: 'Скасовано',
        indeterminate: 'Невизначено',
        loaded: 'Завантажено',
        empty: 'Порожньо',
        active: 'Активно',
        inactive: 'Неактивно',
      },
      runtime: {
        loading: 'Підключення', ready: 'Живий API', error: 'API недоступний', refreshing: 'Оновлення',
        loadingTitle: 'Підключення до FoxForge', loadingText: 'Завантажуємо актуальний стан принтерів і черги.',
        errorTitle: 'Живі дані тимчасово недоступні', errorText: 'Інтерфейс продовжує працювати. Перевірте зв’язок із сервером або повторіть спробу.', retry: 'Повторити',
      },
    },
  },
} as const;

for (const language of ['en', 'ru', 'uk'] as const) {
  i18n.addResourceBundle(language, 'translation', extras[language], true, true);
}

export { extras as alphaTranslationExtras };
