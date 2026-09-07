// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import i18n from './i18n';

export const thermalTelemetryTranslations = {
  en: {
    eyebrow: 'Live thermal telemetry',
    title: 'Temperatures',
    current: 'Current',
    target: 'Target',
    stale: 'Last reported',
    noReading: 'No temperature reading',
    kinds: {
      hotend: 'Hotend',
      bed: 'Bed',
      chamber: 'Chamber',
      other: 'Thermal zone',
    },
  },
  ru: {
    eyebrow: 'Температуры в реальном времени',
    title: 'Температуры',
    current: 'Сейчас',
    target: 'Цель',
    stale: 'Последние данные',
    noReading: 'Нет данных о температуре',
    kinds: {
      hotend: 'Хотэнд',
      bed: 'Стол',
      chamber: 'Камера',
      other: 'Температурная зона',
    },
  },
  uk: {
    eyebrow: 'Температури в реальному часі',
    title: 'Температури',
    current: 'Зараз',
    target: 'Ціль',
    stale: 'Останні дані',
    noReading: 'Немає даних про температуру',
    kinds: {
      hotend: 'Хотенд',
      bed: 'Стіл',
      chamber: 'Камера',
      other: 'Температурна зона',
    },
  },
} as const;

for (const language of ['en', 'ru', 'uk'] as const) {
  i18n.addResourceBundle(
    language,
    'translation',
    { thermalTelemetry: thermalTelemetryTranslations[language] },
    true,
    true,
  );
}
