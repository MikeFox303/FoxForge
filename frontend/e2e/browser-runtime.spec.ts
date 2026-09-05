// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test } from '@playwright/test';

const routes = ['/', '/printers', '/queue', '/materials', '/inventory', '/farm', '/system'];

for (const route of routes) {
  test(`route ${route} has no browser runtime errors`, async ({ page }) => {
    const errors: string[] = [];

    page.on('pageerror', (error) => {
      errors.push(`pageerror: ${error.message}`);
    });
    page.on('console', (message) => {
      if (message.type() === 'error') {
        errors.push(`console.error: ${message.text()}`);
      }
    });

    await page.goto(route);
    await expect(page.locator('.app-shell')).toBeVisible();
    await expect(page.locator('.content')).toBeVisible();

    expect(errors).toEqual([]);
  });
}
