// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test, type Page } from '@playwright/test';

const operatorToken = process.env.FOXFORGE_E2E_COMMAND_TOKEN
  ?? 'foxforge-e2e-command-token-0123456789abcdef';
const observedAt = '2026-09-08T05:00:00Z';
const queueId = '153b6d90-5bb1-49fd-b90a-4316ba57db88';
const spoolId = '20fdc5cb-7af3-4c3d-8f50-a97ff26c02f5';

async function unlockWrites(page: Page): Promise<void> {
  const access = page.locator('.operator-access-shell');
  await expect(access).toBeVisible();
  const input = access.locator('input[type="password"]');
  if (!(await input.isVisible())) await access.locator('.operator-access-toggle').click();
  await input.fill(operatorToken);
  await access.getByRole('button', { name: /unlock writes/i }).click();
  await expect(access).toContainText(/writes unlocked for this tab/i);
}

function fleet() {
  return {
    apiVersion: '1',
    printers: [{
      identity: {
        printerId: 'accounting-printer',
        displayName: 'Accounting Printer',
        vendor: 'test',
        model: 'Dual',
        serialNumber: 'ACCOUNTING-001',
        adapterKind: 'fake',
      },
      snapshot: {
        printerId: 'accounting-printer',
        connection: 'connected',
        operationalState: 'idle',
        activeJob: null,
        observedAt,
        stale: false,
        faultSummary: [],
      },
      capabilities: [{
        capabilityId: 'foxforge.print_execution',
        majorVersion: 1,
        acceptedFormats: ['3mf'],
        supportsMaterialBindings: true,
      }],
      materialSystem: {
        printerId: 'accounting-printer',
        observedAt,
        stale: false,
        units: [{
          unitId: 'ams-0',
          kind: 'multi_slot',
          label: 'AMS 2 Pro',
          position: 0,
          slots: [{
            slotId: 'slot-a1',
            unitId: 'ams-0',
            position: 0,
            label: 'A1',
            presence: 'loaded',
            activity: 'inactive',
            detectedMaterial: {
              materialFamily: 'PETG',
              vendorName: 'SUNLU',
              productName: 'PETG Black',
              rgbaHex: '202124FF',
              tag: null,
              remainingFraction: 0.8,
            },
          }],
        }],
      },
      materialTopology: {
        printerId: 'accounting-printer',
        observedAt,
        stale: false,
        toolheads: [{ toolheadId: 'toolhead-left', label: 'Left toolhead', position: 1 }],
        routes: [{ sourceSlotId: 'slot-a1', toolheadIds: ['toolhead-left'], kind: 'fixed' }],
      },
    }],
  };
}

function queueEntry(state = 'pending', attemptCount = 0) {
  return {
    queueId,
    printerId: 'accounting-printer',
    state,
    createdAt: observedAt,
    updatedAt: observedAt,
    attemptCount,
    request: {
      requestedName: 'Accounting part',
      artifact: { filename: 'accounting.3mf', format: '3mf' },
      materialBindings: [{ materialIndex: 0, slotId: 'slot-a1', toolheadId: 'toolhead-left' }],
    },
    assessment: null,
    error: null,
  };
}

function spool(spoolOverride = spoolId, assignment = true) {
  return {
    spoolId: spoolOverride,
    materialFamily: spoolOverride === spoolId ? 'PETG' : 'PLA',
    manufacturer: spoolOverride === spoolId ? 'SUNLU' : 'Replacement',
    productName: spoolOverride === spoolId ? 'PETG Black' : 'PLA White',
    rgbaHex: null,
    initialFilamentMassG: '1000',
    remainingFilamentMassG: '800',
    usedFilamentMassG: '200',
    usedFraction: '0.2',
    emptySpoolMassG: '180',
    purchaseDate: null,
    archived: false,
    assignment: assignment ? { printerId: 'accounting-printer', slotId: 'slot-a1', assignedAt: observedAt } : null,
  };
}

async function mockReadModels(
  page: Page,
  options: {
    state?: string;
    attemptCount?: number;
    reservations: Array<Record<string, unknown>>;
    inventorySpools?: Array<Record<string, unknown>>;
  },
) {
  await page.route('**/api/v1/fleet', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fleet()) });
  });
  await page.route('**/api/v1/queue', async (route) => {
    if (route.request().method() !== 'GET') return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        apiVersion: '1',
        entries: [queueEntry(options.state, options.attemptCount)],
      }),
    });
  });
  await page.route('**/api/v1/inventory/spools', async (route) => {
    if (route.request().method() !== 'GET') return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ apiVersion: '1', spools: options.inventorySpools ?? [spool()] }),
    });
  });
  await page.route('**/api/v1/filament-accounting', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ apiVersion: '1', reservations: options.reservations, spools: [] }),
    });
  });
}

test('operator reserves explicit grams against the queue saved routing without resubmitting routing intent', async ({ page }) => {
  const reservations: Array<Record<string, unknown>> = [];
  let planPayload: unknown = null;
  let planIdempotencyKey: string | undefined;
  await mockReadModels(page, { reservations });
  await page.route(`**/api/v1/queue/${queueId}/filament-plan`, async (route) => {
    planPayload = route.request().postDataJSON();
    planIdempotencyKey = route.request().headers()['idempotency-key'];
    reservations.splice(0, reservations.length, {
      queueId,
      materialIndex: 0,
      spoolId,
      printerId: 'accounting-printer',
      slotId: 'slot-a1',
      estimatedMassG: '24.650',
      actualMassG: null,
      state: 'reserved',
      createdAt: observedAt,
      updatedAt: observedAt,
      note: null,
    });
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ apiVersion: '1', queueId, reservations, replayed: false }),
    });
  });

  await page.goto('/queue');
  await unlockWrites(page);
  const accounting = page.locator('.queue-accounting-panel');
  await expect(accounting).toBeVisible();
  await expect(accounting).toContainText('A1');
  await expect(accounting).toContainText('Left toolhead');
  await expect(accounting).toContainText('SUNLU · PETG Black · PETG');

  await accounting.getByLabel('Estimated mass').fill('24.650');
  await accounting.getByRole('button', { name: /reserve filament/i }).click();

  await expect.poll(() => planPayload).toEqual({
    estimates: [{ materialIndex: 0, estimatedMassG: '24.650' }],
  });
  expect(JSON.stringify(planPayload)).not.toContain('slotId');
  expect(JSON.stringify(planPayload)).not.toContain('toolheadId');
  expect(planIdempotencyKey).toBeTruthy();
  await expect(accounting).toContainText('Reserved');
  await expect(accounting).toContainText('24.650 g');
});

test('reconciliation keeps the original reserved spool visible and surfaces assignment drift', async ({ page }) => {
  const replacementId = '30fdc5cb-7af3-4c3d-8f50-a97ff26c02f6';
  const reservations: Array<Record<string, unknown>> = [{
    queueId,
    materialIndex: 0,
    spoolId,
    printerId: 'accounting-printer',
    slotId: 'slot-a1',
    estimatedMassG: '20.000',
    actualMassG: null,
    state: 'reconciliation_required',
    createdAt: observedAt,
    updatedAt: observedAt,
    note: 'print crossed start boundary',
  }];
  let reconcilePayload: unknown = null;
  await mockReadModels(page, {
    state: 'failed',
    attemptCount: 1,
    reservations,
    inventorySpools: [spool(spoolId, false), spool(replacementId, true)],
  });
  await page.route(`**/api/v1/queue/${queueId}/filament-reconcile`, async (route) => {
    reconcilePayload = route.request().postDataJSON();
    reservations[0] = {
      ...reservations[0],
      actualMassG: '8.400',
      state: 'consumed',
      note: 'weighed after print',
    };
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ apiVersion: '1', queueId, reservations, replayed: false }),
    });
  });

  await page.goto('/queue');
  await unlockWrites(page);
  const accounting = page.locator('.queue-accounting-panel');
  await expect(accounting).toContainText('Physical assignment changed');
  await expect(accounting).toContainText('SUNLU · PETG Black · PETG');
  await expect(accounting).toContainText('Replacement · PLA White · PLA');

  await accounting.getByLabel('Actual consumed mass').fill('8.400');
  await accounting.getByLabel('Reconciliation note').fill('weighed after print');
  await accounting.getByRole('button', { name: /save reconciliation/i }).click();

  await expect.poll(() => reconcilePayload).toEqual({
    materialIndex: 0,
    actualMassG: '8.400',
    note: 'weighed after print',
  });
  await expect(accounting).toContainText('Consumed');
  await expect(accounting).toContainText('8.400 g');
});

test('accounting panel stays within the phone viewport', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'phone');
  await mockReadModels(page, { reservations: [] });
  await page.goto('/queue');

  const accounting = page.locator('.queue-accounting-panel');
  await expect(accounting).toBeVisible();
  const box = await accounting.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(page.viewportSize()!.width + 1);
});
