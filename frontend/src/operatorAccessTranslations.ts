// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import i18n from './i18n';

export const operatorAccessTranslations = {
  en: {
    token: 'Operator command token',
    placeholder: 'Operator token',
    unlock: 'Unlock writes',
    checking: 'Checking…',
    unlocked: 'Writes unlocked for this tab',
    lock: 'Lock',
    invalid: 'The operator token is invalid.',
    disabled: 'Write commands are disabled for this deployment. Configure FOXFORGE_COMMAND_TOKEN first.',
    credentialHelp: 'Umbrel: use the FoxForge app password shown in the app menu. Docker: use FOXFORGE_COMMAND_TOKEN.',
  },
  ru: {
    token: 'Токен оператора',
    placeholder: 'Токен оператора',
    unlock: 'Разблокировать запись',
    checking: 'Проверка…',
    unlocked: 'Запись разблокирована для этой вкладки',
    lock: 'Заблокировать',
    invalid: 'Токен оператора недействителен.',
    disabled: 'Команды записи отключены для этой установки. Сначала настройте FOXFORGE_COMMAND_TOKEN.',
    credentialHelp: 'Umbrel: используйте пароль приложения FoxForge, показанный в меню приложения. Docker: используйте FOXFORGE_COMMAND_TOKEN.',
  },
  uk: {
    token: 'Токен оператора',
    placeholder: 'Токен оператора',
    unlock: 'Розблокувати запис',
    checking: 'Перевірка…',
    unlocked: 'Запис розблоковано для цієї вкладки',
    lock: 'Заблокувати',
    invalid: 'Токен оператора недійсний.',
    disabled: 'Команди запису вимкнені для цього встановлення. Спочатку налаштуйте FOXFORGE_COMMAND_TOKEN.',
    credentialHelp: 'Umbrel: використовуйте пароль застосунку FoxForge, показаний у меню застосунку. Docker: використовуйте FOXFORGE_COMMAND_TOKEN.',
  },
} as const;

for (const language of ['en', 'ru', 'uk'] as const) {
  i18n.addResourceBundle(language, 'translation', { operatorAccess: operatorAccessTranslations[language] }, true, true);
}
