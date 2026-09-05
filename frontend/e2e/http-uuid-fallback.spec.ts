// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test } from '@playwright/test';

test('restores randomUUID when the browser exposes Web Crypto without randomUUID', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(Crypto.prototype, 'randomUUID', {
      configurable: true,
      value: undefined,
      writable: true,
    });
  });

  await page.goto('/');
  await expect(page.locator('#root')).toContainText('FoxForge');

  const uuid = await page.evaluate(() => crypto.randomUUID());
  expect(uuid).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});
