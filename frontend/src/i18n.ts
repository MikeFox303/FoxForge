// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import { en } from './locales/en';
import { ru } from './locales/ru';
import { uk } from './locales/uk';

const resources = {
  en: { translation: en },
  ru: { translation: ru },
  uk: { translation: uk },
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
  if (typeof window !== 'undefined') window.localStorage.setItem('foxforge.language', language);
}

export default i18n;
