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
    },
  },
} as const;

for (const language of ['en', 'ru', 'uk'] as const) {
  i18n.addResourceBundle(language, 'translation', extras[language], true, true);
}

export { extras as alphaTranslationExtras };
