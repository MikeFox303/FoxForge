// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      nav: {
        overview: 'Overview',
        printers: 'Printers',
        queue: 'Print queue',
        materials: 'Materials',
        farm: 'Farm',
        system: 'System',
      },
      shell: {
        workspace: 'FoxForge workspace',
        preview: 'Preview data',
        addPrinter: 'Add printer',
        developmentPreview: 'Development preview',
        demoData: 'Demo data · pre-alpha',
        support: 'Support on Ko-fi',
      },
      language: {
        title: 'Interface language',
        english: 'English',
        russian: 'Русский',
        ukrainian: 'Українська',
      },
    },
  },
  ru: {
    translation: {
      nav: {
        overview: 'Обзор',
        printers: 'Принтеры',
        queue: 'Очередь печати',
        materials: 'Материалы',
        farm: 'Ферма',
        system: 'Система',
      },
      shell: {
        workspace: 'Рабочее пространство FoxForge',
        preview: 'Демо-данные',
        addPrinter: 'Добавить принтер',
        developmentPreview: 'Предварительная версия',
        demoData: 'Демо-данные · pre-alpha',
        support: 'Поддержать на Ko-fi',
      },
      language: {
        title: 'Язык интерфейса',
        english: 'English',
        russian: 'Русский',
        ukrainian: 'Українська',
      },
    },
  },
  uk: {
    translation: {
      nav: {
        overview: 'Огляд',
        printers: 'Принтери',
        queue: 'Черга друку',
        materials: 'Матеріали',
        farm: 'Ферма',
        system: 'Система',
      },
      shell: {
        workspace: 'Робочий простір FoxForge',
        preview: 'Демо-дані',
        addPrinter: 'Додати принтер',
        developmentPreview: 'Попередня версія',
        demoData: 'Демо-дані · pre-alpha',
        support: 'Підтримати на Ko-fi',
      },
      language: {
        title: 'Мова інтерфейсу',
        english: 'English',
        russian: 'Русский',
        ukrainian: 'Українська',
      },
    },
  },
} as const;

const storedLanguage = typeof window !== 'undefined' ? window.localStorage.getItem('foxforge.language') : null;
const initialLanguage = storedLanguage && ['en', 'ru', 'uk'].includes(storedLanguage) ? storedLanguage : 'en';

void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage,
  fallbackLng: 'en',
  supportedLngs: ['en', 'ru', 'uk'],
  interpolation: { escapeValue: false },
});

export async function changeInterfaceLanguage(language: 'en' | 'ru' | 'uk'): Promise<void> {
  await i18n.changeLanguage(language);
  if (typeof window !== 'undefined') {
    window.localStorage.setItem('foxforge.language', language);
  }
}

export default i18n;
