// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import i18n from './i18n';

export const jobControlTranslations = {
  en: {
    controls: 'Print controls',
    identityRequired: 'FoxForge cannot safely control this print because the printer did not report a vendor job identity.',
    confirmCancel: 'Cancel the active print? FoxForge will target only the currently verified printer job.',
    sending: 'Sending…',
    uncertain: 'The printer-control outcome is uncertain. FoxForge will not retry automatically. Wait for a fresh printer state and verify the physical printer before sending another control command.',
    actions: { pause: 'Pause', resume: 'Resume', cancel: 'Cancel print' },
    accepted: { pause: 'Pause command accepted.', resume: 'Resume command accepted.', cancel: 'Cancel command accepted.' },
  },
  ru: {
    controls: 'Управление печатью',
    identityRequired: 'FoxForge не может безопасно управлять этой печатью: принтер не сообщил идентификатор задания производителя.',
    confirmCancel: 'Отменить текущую печать? FoxForge отправит команду только для подтверждённого текущего задания принтера.',
    sending: 'Отправка…',
    uncertain: 'Результат команды управления неизвестен. FoxForge не будет повторять её автоматически. Дождитесь свежего состояния принтера и проверьте сам принтер перед новой командой.',
    actions: { pause: 'Пауза', resume: 'Продолжить', cancel: 'Отменить печать' },
    accepted: { pause: 'Команда паузы принята.', resume: 'Команда продолжения принята.', cancel: 'Команда отмены принята.' },
  },
  uk: {
    controls: 'Керування друком',
    identityRequired: 'FoxForge не може безпечно керувати цим друком: принтер не повідомив ідентифікатор завдання виробника.',
    confirmCancel: 'Скасувати поточний друк? FoxForge надішле команду лише для підтвердженого поточного завдання принтера.',
    sending: 'Надсилання…',
    uncertain: 'Результат команди керування невідомий. FoxForge не повторюватиме її автоматично. Дочекайтеся свіжого стану принтера та перевірте сам принтер перед новою командою.',
    actions: { pause: 'Пауза', resume: 'Продовжити', cancel: 'Скасувати друк' },
    accepted: { pause: 'Команду паузи прийнято.', resume: 'Команду продовження прийнято.', cancel: 'Команду скасування прийнято.' },
  },
} as const;

for (const language of ['en', 'ru', 'uk'] as const) {
  i18n.addResourceBundle(language, 'translation', { jobControl: jobControlTranslations[language] }, true, true);
}
