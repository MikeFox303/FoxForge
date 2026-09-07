// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import i18n from './i18n';

export const operatorAccessTranslations = {
  en: {
    token: 'Operator command token',
    placeholder: 'Operator token',
    unlock: 'Unlock writes',
    checking: 'Checking…',
    locked: 'Writes locked',
    unlocked: 'Writes unlocked for this tab',
    lock: 'Lock',
    invalid: 'The operator token is invalid.',
    disabled: 'Write commands are disabled for this deployment. Configure FOXFORGE_COMMAND_TOKEN first.',
    credentialHelp: 'Umbrel: use the FoxForge app password shown in the app menu. Docker: use FOXFORGE_COMMAND_TOKEN.',
    memoryHelp: 'The credential is kept only in memory for this tab and is cleared on page reload or Lock.',
  },
  ru: {
    token: 'Токен оператора',
    placeholder: 'Токен оператора',
    unlock: 'Разблокировать запись',
    checking: 'Проверка…',
    locked: 'Запись заблокирована',
    unlocked: 'Запись разблокирована для этой вкладки',
    lock: 'Заблокировать',
    invalid: 'Токен оператора недействителен.',
    disabled: 'Команды записи отключены для этой установки. Сначала настройте FOXFORGE_COMMAND_TOKEN.',
    credentialHelp: 'Umbrel: используйте пароль приложения FoxForge, показанный в меню приложения. Docker: используйте FOXFORGE_COMMAND_TOKEN.',
    memoryHelp: 'Учётные данные хранятся только в памяти этой вкладки и очищаются при перезагрузке страницы или блокировке.',
  },
  uk: {
    token: 'Токен оператора',
    placeholder: 'Токен оператора',
    unlock: 'Розблокувати запис',
    checking: 'Перевірка…',
    locked: 'Запис заблоковано',
    unlocked: 'Запис розблоковано для цієї вкладки',
    lock: 'Заблокувати',
    invalid: 'Токен оператора недійсний.',
    disabled: 'Команди запису вимкнені для цього встановлення. Спочатку налаштуйте FOXFORGE_COMMAND_TOKEN.',
    credentialHelp: 'Umbrel: використовуйте пароль застосунку FoxForge, показаний у меню застосунку. Docker: використовуйте FOXFORGE_COMMAND_TOKEN.',
    memoryHelp: 'Облікові дані зберігаються лише в пам’яті цієї вкладки та очищаються після перезавантаження сторінки або блокування.',
  },
} as const;

for (const language of ['en', 'ru', 'uk'] as const) {
  i18n.addResourceBundle(language, 'translation', { operatorAccess: operatorAccessTranslations[language] }, true, true);
}
