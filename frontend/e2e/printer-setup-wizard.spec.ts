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

function successfulOutcome(host: string) {
  return {
    configuration: {
      printerId: 'bambu-01p00a000000001',
      displayName: 'X2D Main',
      kind: 'bambu',
      vendor: 'Bambu Lab',
      model: 'X2D',
      serialNumber: '01P00A000000001',
      connection: { host, accessCodeConfigured: true },
    },
    connection: 'connected',
    operationalState: 'idle',
    observedAt: '2026-09-06T17:00:00Z',
    reachable: true,
    connectionError: null,
  };
}

test('Add Printer requires verification of the exact current payload before save', async ({ page }) => {
  let verifyRequests = 0;
  let addRequests = 0;
  let lastAddedHost: string | undefined;

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
      body: JSON.stringify({ apiVersion: '1', subnets: ['192.168.50.0/24'] }),
    });
  });
  await page.route('**/api/v1/printers/test-connection', async (route) => {
    verifyRequests += 1;
    const payload = route.request().postDataJSON() as { connection: { host?: string } };
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(successfulOutcome(payload.connection.host ?? '')),
    });
  });
  await page.route('**/api/v1/printers', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback();
      return;
    }
    addRequests += 1;
    const payload = route.request().postDataJSON() as { connection: { host?: string } };
    lastAddedHost = payload.connection.host;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(successfulOutcome(payload.connection.host ?? '')),
    });
  });

  await page.goto('/');
  await unlockWrites(page);
  await page.locator('.printer-setup-launcher').click();

  const dialog = page.locator('.setup-dialog');
  await expect(dialog.locator('.setup-provider-card.active')).toContainText(/Bambu Lab/i);
  await dialog.getByRole('button', { name: /^Next$/i }).click();

  await dialog.getByLabel(/Printer IP \/ hostname/i).fill('192.168.50.44');
  await dialog.getByLabel(/LAN access code/i).fill('12345678');
  await dialog.getByRole('button', { name: /^Next$/i }).click();

  await dialog.getByLabel(/^Display name$/i).fill('X2D Main');
  await dialog.getByLabel(/Model/i).selectOption('X2D');
  await dialog.getByLabel(/^Serial number$/i).fill('01P00A000000001');
  await dialog.getByRole('button', { name: /^Next$/i }).click();

  const save = dialog.getByRole('button', { name: /Save and connect/i });
  const verify = dialog.getByRole('button', { name: /Verify connection/i });
  await expect(save).toBeDisabled();
  expect(addRequests).toBe(0);

  await verify.click();
  await expect.poll(() => verifyRequests).toBe(1);
  await expect(save).toBeEnabled();
  expect(addRequests).toBe(0);

  await dialog.getByRole('button', { name: /^Back$/i }).click();
  await dialog.getByRole('button', { name: /^Back$/i }).click();
  await dialog.getByLabel(/Printer IP \/ hostname/i).fill('192.168.50.45');
  await dialog.getByRole('button', { name: /^Next$/i }).click();
  await dialog.getByRole('button', { name: /^Next$/i }).click();

  await expect(save).toBeDisabled();
  await expect(dialog.locator('.setup-verification-state')).toContainText(/Any change after verification requires a new check/i);
  expect(addRequests).toBe(0);

  await verify.click();
  await expect.poll(() => verifyRequests).toBe(2);
  await expect(save).toBeEnabled();
  await save.click();

  await expect.poll(() => addRequests).toBe(1);
  expect(lastAddedHost).toBe('192.168.50.45');
});
