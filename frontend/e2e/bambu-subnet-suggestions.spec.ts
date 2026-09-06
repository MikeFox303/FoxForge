// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test, type Page } from '@playwright/test';

const operatorToken = process.env.FOXFORGE_E2E_COMMAND_TOKEN
  ?? 'foxforge-e2e-command-token-0123456789abcdef';

async function unlockWrites(page: Page): Promise<void> {
  const access = page.locator('.operator-access-shell');
  await expect(access).toBeVisible();
  const input = access.locator('input[type="password"]');
  if (!(await input.isVisible())) await access.locator('.operator-access-toggle').click();
  await input.fill(operatorToken);
  await access.getByRole('button', { name: /unlock writes/i }).click();
  await expect(access).toContainText(/writes unlocked for this tab/i);
}

test('Bambu setup suggests bounded server-visible networks without auto-scanning', async ({ page }) => {
  let scanRequests = 0;
  let scannedSubnet: string | undefined;

  await page.route('**/api/v1/printers/configuration', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ apiVersion: '1', printers: [] }),
    });
  });
  await page.route('**/api/v1/printers/discovery/bambu/subnets', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ apiVersion: '1', subnets: ['10.42.0.0/24', '192.168.50.0/24'] }),
    });
  });
  await page.route('**/api/v1/printers/discovery/bambu', async (route) => {
    scanRequests += 1;
    scannedSubnet = (route.request().postDataJSON() as { subnet?: string }).subnet;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ apiVersion: '1', candidates: [] }),
    });
  });

  await page.goto('/');
  await unlockWrites(page);
  await page.locator('.printer-setup-launcher').click();

  const dialog = page.locator('.setup-dialog');
  await expect(dialog).toBeVisible();
  const suggestions = dialog.locator('.setup-subnet-buttons button');
  await expect(suggestions).toHaveCount(2);
  await expect(suggestions.nth(0)).toHaveText('10.42.0.0/24');
  await expect(suggestions.nth(1)).toHaveText('192.168.50.0/24');
  expect(scanRequests).toBe(0);

  const subnetInput = dialog.getByLabel(/subnet to scan/i);
  await expect(subnetInput).toHaveValue('10.42.0.0/24');
  await suggestions.nth(1).click();
  await expect(subnetInput).toHaveValue('192.168.50.0/24');
  expect(scanRequests).toBe(0);

  await dialog.getByRole('button', { name: /scan subnet/i }).click();
  await expect.poll(() => scanRequests).toBe(1);
  expect(scannedSubnet).toBe('192.168.50.0/24');
});

test('Bambu setup keeps manual CIDR fallback when the server sees no private network', async ({ page }) => {
  await page.route('**/api/v1/printers/configuration', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ apiVersion: '1', printers: [] }),
    });
  });
  await page.route('**/api/v1/printers/discovery/bambu/subnets', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ apiVersion: '1', subnets: [] }),
    });
  });

  await page.goto('/');
  await unlockWrites(page);
  await page.locator('.printer-setup-launcher').click();

  const dialog = page.locator('.setup-dialog');
  await expect(dialog).toContainText(/enter the printer subnet manually/i);
  const subnetInput = dialog.getByLabel(/subnet to scan/i);
  await expect(subnetInput).toHaveValue('');
  await subnetInput.fill('192.168.77.0/24');
  await expect(subnetInput).toHaveValue('192.168.77.0/24');
});
