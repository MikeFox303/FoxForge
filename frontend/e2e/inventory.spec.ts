// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test, type Page } from '@playwright/test';

const operatorToken = process.env.FOXFORGE_E2E_COMMAND_TOKEN
  ?? 'foxforge-e2e-command-token-0123456789abcdef';

async function unlockWrites(page: Page): Promise<void> {
  const access = page.locator('.operator-access-shell');
  await access.locator('input[type="password"]').fill(operatorToken);
  await access.getByRole('button', { name: /unlock writes/i }).click();
  await expect(access).toContainText(/writes unlocked for this tab/i);
}

test('inventory operator can create, correct, inspect history and archive through the production API', async ({ page }) => {
  await page.goto('/inventory');
  await unlockWrites(page);

  await page.getByRole('button', { name: /^add spool$/i }).click();
  const create = page.getByRole('dialog', { name: /add spool/i });
  await create.getByLabel('Material').fill('PETG');
  await create.getByLabel('Manufacturer').fill('FoxForge E2E');
  await create.getByLabel('Product').fill('Operator spool');
  await create.getByLabel('Initial filament mass (g)').fill('1000.000');
  await create.getByLabel('Empty spool mass (g)').fill('180.50');
  await create.getByRole('button', { name: /^add spool$/i }).click();

  const card = page.locator('.spool-card').filter({ hasText: 'Operator spool' });
  await expect(card).toBeVisible();
  await expect(card).toContainText('1000 g');

  await card.getByRole('button', { name: /correct mass/i }).click();
  const correction = page.getByRole('dialog', { name: /correct remaining mass/i });
  await correction.getByLabel('Remaining filament mass (g)').fill('735.5');
  await correction.getByLabel('Note').fill('browser scale correction');
  await correction.getByRole('button', { name: /^save$/i }).click();
  await expect(card).toContainText('735.5 g');

  await card.getByRole('button', { name: /^history$/i }).click();
  const history = page.getByRole('dialog', { name: /spool history/i });
  await expect(history).toContainText('Correction');
  await expect(history).toContainText('-264.5 g');
  await expect(history).toContainText('browser scale correction');
  await history.getByRole('button', { name: /^close$/i }).click();

  page.once('dialog', (dialog) => void dialog.accept());
  await card.getByRole('button', { name: /^archive$/i }).click();
  await expect(card).toBeHidden();

  await page.getByText('Show archived').click();
  await expect(page.locator('.spool-card').filter({ hasText: 'Operator spool' })).toContainText('Archived');
});

test('inventory assignment UI preserves the opaque physical slot identity', async ({ page }) => {
  let assignmentBody: unknown = null;
  await page.route('**/api/v1/fleet', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        apiVersion: '1',
        printers: [{
          identity: {
            printerId: 'x2d-main', displayName: 'Bambu X2D', vendor: 'bambu_lab', model: 'X2D', adapterKind: 'fake',
          },
          snapshot: {
            printerId: 'x2d-main', connection: 'connected', operationalState: 'idle', activeJob: null,
            observedAt: '2026-09-05T00:00:00Z', stale: false, faultSummary: [],
          },
          capabilities: [{ capabilityId: 'foxforge.material_system', majorVersion: 1 }],
          materialSystem: {
            printerId: 'x2d-main', observedAt: '2026-09-05T00:00:00Z', stale: false,
            units: [{
              unitId: 'bambu:unit:0', kind: 'multi_slot', label: 'AMS 2 Pro', position: 0,
              slots: [{
                slotId: 'bambu:unit:0:tray:3', unitId: 'bambu:unit:0', position: 3, label: 'A4',
                presence: 'empty', activity: 'inactive', detectedMaterial: null,
              }],
            }],
          },
        }],
      }),
    });
  });
  await page.route('**/api/v1/inventory/spools', async (route) => {
    if (route.request().method() !== 'GET') return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        apiVersion: '1',
        spools: [{
          spoolId: '20fdc5cb-7af3-4c3d-8f50-a97ff26c02f5', materialFamily: 'PETG', manufacturer: 'SUNLU',
          productName: 'PETG', rgbaHex: '#FF6600', initialFilamentMassG: '1000', remainingFilamentMassG: '800',
          usedFilamentMassG: '200', usedFraction: '0.2', emptySpoolMassG: '180', purchaseDate: null, archived: false,
          assignment: null,
        }],
      }),
    });
  });
  await page.route('**/api/v1/inventory/spools/*/assignment', async (route) => {
    assignmentBody = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

  await page.goto('/inventory');
  await unlockWrites(page);
  const card = page.locator('.spool-card').filter({ hasText: 'SUNLU PETG' });
  await card.getByRole('button', { name: /assign or move spool/i }).click();
  const move = page.getByRole('dialog', { name: /assign or move spool/i });
  await move.getByLabel('Printer slot').selectOption({ label: 'Bambu X2D · AMS 2 Pro · A4' });
  await move.getByRole('button', { name: /^save$/i }).click();

  await expect.poll(() => assignmentBody).toEqual({ printerId: 'x2d-main', slotId: 'bambu:unit:0:tray:3' });
});
