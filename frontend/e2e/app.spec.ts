// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test } from '@playwright/test';

const operatorToken = process.env.FOXFORGE_E2E_COMMAND_TOKEN
  ?? 'foxforge-e2e-command-token-0123456789abcdef';

test('SPA routes and the single Add Printer entry point remain usable', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.app-shell')).toBeVisible();
  await expect(page.locator('.printer-setup-launcher')).toHaveCount(1);
  await expect(page.locator('.printer-setup-launcher')).toBeVisible();

  await page.goto('/printers');
  await expect(page.locator('.printer-setup-launcher')).toHaveCount(1);
  await expect(page.locator('.printer-setup-launcher')).toBeVisible();

  await page.locator('.printer-setup-launcher').click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
});

test('operator write access is explicit and memory-only for the active tab', async ({ page }) => {
  await page.goto('/');
  const access = page.locator('.operator-access-shell');
  await expect(access).toBeVisible();

  await access.locator('input[type="password"]').fill(operatorToken);
  await access.getByRole('button', { name: /unlock writes/i }).click();
  await expect(access).toContainText(/writes unlocked for this tab/i);

  const persistentCopy = await page.evaluate(() => ({
    local: Object.values(localStorage),
    session: Object.values(sessionStorage),
    url: location.href,
  }));
  expect(JSON.stringify(persistentCopy)).not.toContain(operatorToken);

  await access.getByRole('button', { name: /^lock$/i }).click();
  await expect(access.locator('input[type="password"]')).toBeVisible();
});
