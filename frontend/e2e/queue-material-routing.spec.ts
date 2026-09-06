// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test, type Page } from '@playwright/test';

const operatorToken = process.env.FOXFORGE_E2E_COMMAND_TOKEN
  ?? 'foxforge-e2e-command-token-0123456789abcdef';
const observedAt = '2026-09-06T00:00:00Z';

async function unlockWrites(page: Page): Promise<void> {
  const access = page.locator('.operator-access-shell');
  await expect(access).toBeVisible();
  const input = access.locator('input[type="password"]');
  if (!(await input.isVisible())) await access.locator('.operator-access-toggle').click();
  await input.fill(operatorToken);
  await access.getByRole('button', { name: /unlock writes/i }).click();
  await expect(access).toContainText(/writes unlocked for this tab/i);
}

function routedFleet() {
  return {
    apiVersion: '1',
    printers: [
      {
        identity: {
          printerId: 'routed-printer',
          displayName: 'Routed Browser Printer',
          vendor: 'test',
          model: 'Dual',
          serialNumber: 'ROUTED-001',
          adapterKind: 'fake',
        },
        snapshot: {
          printerId: 'routed-printer',
          connection: 'connected',
          operationalState: 'idle',
          activeJob: null,
          observedAt,
          stale: false,
          faultSummary: [],
        },
        capabilities: [
          {
            capabilityId: 'foxforge.print_execution',
            majorVersion: 1,
            acceptedFormats: ['3mf'],
            supportsPlateSelection: true,
            supportsMaterialBindings: true,
          },
        ],
        materialSystem: {
          printerId: 'routed-printer',
          observedAt,
          stale: false,
          units: [
            {
              unitId: 'ams-0',
              kind: 'multi_slot',
              label: 'AMS',
              position: 0,
              slots: [
                {
                  slotId: 'slot-petg',
                  unitId: 'ams-0',
                  position: 0,
                  label: 'A1',
                  presence: 'loaded',
                  activity: 'idle',
                  detectedMaterial: {
                    materialFamily: 'PETG',
                    vendorName: null,
                    productName: null,
                    rgbaHex: 'FFFFFFFF',
                    tag: null,
                    remainingFraction: null,
                  },
                },
                {
                  slotId: 'slot-pla',
                  unitId: 'ams-0',
                  position: 1,
                  label: 'A2',
                  presence: 'loaded',
                  activity: 'idle',
                  detectedMaterial: {
                    materialFamily: 'PLA',
                    vendorName: null,
                    productName: null,
                    rgbaHex: '000000FF',
                    tag: null,
                    remainingFraction: null,
                  },
                },
              ],
            },
          ],
        },
        materialTopology: {
          printerId: 'routed-printer',
          observedAt,
          stale: false,
          toolheads: [
            { toolheadId: 'toolhead-left', label: 'Left toolhead', position: 1 },
            { toolheadId: 'toolhead-right', label: 'Right toolhead', position: 0 },
          ],
          routes: [
            { sourceSlotId: 'slot-petg', toolheadIds: ['toolhead-left'], kind: 'fixed' },
            { sourceSlotId: 'slot-pla', toolheadIds: ['toolhead-right'], kind: 'fixed' },
          ],
        },
      },
    ],
  };
}

test('3MF enqueue requires explicit compatible source bindings and never sends toolheadId', async ({ page }) => {
  let inspectRequests = 0;
  let enqueuePayload: Record<string, unknown> | undefined;

  await page.route('**/api/v1/fleet', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(routedFleet()) });
  });
  await page.route('**/api/v1/queue', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ apiVersion: '1', entries: [] }) });
      return;
    }
    enqueuePayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        queueId: enqueuePayload.queueId,
        printerId: enqueuePayload.printerId,
        state: 'pending',
      }),
    });
  });
  await page.route('**/api/v1/artifacts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        artifactId: 'a'.repeat(64),
        filename: 'routed-test.3mf',
        format: '3mf',
        sizeBytes: 32,
        sha256: route.request().headers()['x-foxforge-sha256'],
        replayed: false,
      }),
    });
  });
  await page.route('**/api/v1/artifacts/*/print-plan', async (route) => {
    inspectRequests += 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        artifactId: 'a'.repeat(64),
        artifactSha256: 'a'.repeat(64),
        readyForRouting: true,
        plates: [
          {
            plateIndex: 0,
            readyForRouting: true,
            materialRequirements: [
              {
                materialIndex: 0,
                materialFamily: 'PETG',
                rgbaHex: 'FFFFFFFF',
                profileName: 'PETG profile',
                expectedToolheadPosition: 1,
              },
              {
                materialIndex: 1,
                materialFamily: 'PLA',
                rgbaHex: '000000FF',
                profileName: 'PLA profile',
                expectedToolheadPosition: 0,
              },
            ],
          },
        ],
        issues: [],
      }),
    });
  });

  await page.goto('/queue');
  await unlockWrites(page);

  const panel = page.locator('.queue-command-panel');
  await panel.locator('input[type="file"]').setInputFiles({
    name: 'routed-test.3mf',
    mimeType: 'application/vnd.ms-package.3dmanufacturing-3dmodel+xml',
    buffer: Buffer.from('PK\u0003\u0004foxforge-routing-test'),
  });
  await panel.locator('.queue-command-form select').selectOption('routed-printer');

  const action = panel.locator('.queue-command-actions .primary-button');
  await expect(action).toHaveText(/inspect 3mf materials/i);
  await action.click();
  await expect.poll(() => inspectRequests).toBe(1);

  const review = panel.locator('.queue-routing-review');
  await expect(review).toBeVisible();
  await expect(review.locator('.queue-routing-requirement')).toHaveCount(2);
  await expect(action).toBeDisabled();

  const selectors = review.locator('.queue-routing-requirement select');
  await selectors.nth(0).selectOption('slot-pla');
  await expect(review).toContainText(/does not match/i);
  await expect(action).toBeDisabled();

  await selectors.nth(0).selectOption('slot-petg');
  await selectors.nth(1).selectOption('slot-pla');
  await expect(review.locator('.queue-routing-gate')).toContainText(/server compiler will verify them again/i);
  await expect(action).toBeEnabled();

  await action.click();
  await expect.poll(() => enqueuePayload !== undefined).toBe(true);
  expect(enqueuePayload).toMatchObject({
    printerId: 'routed-printer',
    selection: { plateIndex: 0 },
    materialBindings: [
      { materialIndex: 0, slotId: 'slot-petg' },
      { materialIndex: 1, slotId: 'slot-pla' },
    ],
  });
  expect(JSON.stringify(enqueuePayload)).not.toContain('toolheadId');
  await expect(panel.locator('.queue-command-status')).toContainText(/queued/i);
});

test('material routing review stays single-column and within the phone viewport', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'phone');

  await page.route('**/api/v1/fleet', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(routedFleet()) });
  });
  await page.route('**/api/v1/queue', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ apiVersion: '1', entries: [] }) });
  });
  await page.route('**/api/v1/artifacts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        artifactId: 'b'.repeat(64),
        filename: 'phone.3mf',
        format: '3mf',
        sizeBytes: 16,
        sha256: route.request().headers()['x-foxforge-sha256'],
        replayed: false,
      }),
    });
  });
  await page.route('**/api/v1/artifacts/*/print-plan', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        artifactId: 'b'.repeat(64),
        artifactSha256: 'b'.repeat(64),
        readyForRouting: true,
        plates: [{
          plateIndex: 0,
          readyForRouting: true,
          materialRequirements: [{
            materialIndex: 0,
            materialFamily: 'PETG',
            rgbaHex: null,
            profileName: null,
            expectedToolheadPosition: 1,
          }],
        }],
        issues: [],
      }),
    });
  });

  await page.goto('/queue');
  await unlockWrites(page);
  const panel = page.locator('.queue-command-panel');
  await panel.locator('input[type="file"]').setInputFiles({
    name: 'phone.3mf',
    mimeType: 'application/vnd.ms-package.3dmanufacturing-3dmodel+xml',
    buffer: Buffer.from('PK\u0003\u0004phone-routing'),
  });
  await panel.locator('.queue-command-form select').selectOption('routed-printer');
  await panel.locator('.queue-command-actions .primary-button').click();

  const review = panel.locator('.queue-routing-review');
  await expect(review).toBeVisible();
  const box = await review.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(page.viewportSize()!.width + 1);

  const requirement = review.locator('.queue-routing-requirement').first();
  const requirementBox = await requirement.boundingBox();
  expect(requirementBox).not.toBeNull();
  expect(requirementBox!.x + requirementBox!.width).toBeLessThanOrEqual(page.viewportSize()!.width + 1);
});
