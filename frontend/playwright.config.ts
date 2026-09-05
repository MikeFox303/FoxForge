// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 1,
  use: {
    baseURL: process.env.FOXFORGE_E2E_BASE_URL ?? 'http://127.0.0.1:18080',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'desktop-16-9',
      use: { viewport: { width: 1920, height: 1080 } },
    },
    {
      name: 'desktop-32-9',
      use: { viewport: { width: 5120, height: 1440 } },
    },
    {
      name: 'tablet',
      use: { viewport: { width: 900, height: 1024 } },
    },
    {
      name: 'phone',
      use: {
        viewport: { width: 390, height: 844 },
        deviceScaleFactor: 3,
        hasTouch: true,
        isMobile: true,
      },
    },
  ],
});
