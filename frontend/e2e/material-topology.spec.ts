// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test, type Page } from '@playwright/test';

const observedAt = '2026-09-06T12:00:00Z';

function topologyFleet(stale = false) {
  return {
    apiVersion: '1',
    printers: [
      {
        identity: {
          printerId: 'topology-printer',
          displayName: 'Topology Test Printer',
          vendor: 'test',
          model: 'Dual',
          serialNumber: 'TOPOLOGY-001',
          adapterKind: 'fake',
        },
        snapshot: {
          printerId: 'topology-printer',
          connection: 'connected',
          operationalState: 'idle',
          activeJob: null,
          observedAt,
          stale: false,
          faultSummary: [],
        },
        capabilities: [
          { capabilityId: 'foxforge.material_system', majorVersion: 1 },
          { capabilityId: 'foxforge.material_topology', majorVersion: 1, reportsDynamicRoutes: false },
        ],
        materialSystem: {
          printerId: 'topology-printer',
          observedAt,
          stale: false,
          units: [
            {
              unitId: 'multi-0',
              kind: 'multi_slot',
              label: 'Material Unit',
              position: 0,
              slots: [
                {
                  slotId: 'slot-a1',
                  unitId: 'multi-0',
                  position: 0,
                  label: 'A1',
                  presence: 'loaded',
                  activity: 'inactive',
                  detectedMaterial: { materialFamily: 'PETG', rgbaHex: 'FFFFFFFF' },
                },
              ],
            },
            {
              unitId: 'external-left',
              kind: 'external',
              label: 'External Left',
              position: 1,
              slots: [
                {
                  slotId: 'slot-external-left',
                  unitId: 'external-left',
                  position: 0,
                  label: 'External Left',
                  presence: 'empty',
                  activity: 'inactive',
                },
              ],
            },
            {
              unitId: 'external-right',
              kind: 'external',
              label: 'External Right',
              position: 2,
              slots: [
                {
                  slotId: 'slot-external-right',
                  unitId: 'external-right',
                  position: 0,
                  label: 'External Right',
                  presence: 'loaded',
                  activity: 'inactive',
                  detectedMaterial: { materialFamily: 'PLA', rgbaHex: 'FF0000FF' },
                },
              ],
            },
          ],
        },
        materialTopology: {
          printerId: 'topology-printer',
          observedAt,
          stale,
          toolheads: [
            { toolheadId: 'toolhead-left', label: 'Left toolhead', position: 1 },
            { toolheadId: 'toolhead-right', label: 'Right toolhead', position: 0 },
          ],
          routes: [
            { sourceSlotId: 'slot-external-left', toolheadIds: ['toolhead-left'], kind: 'fixed' },
            { sourceSlotId: 'slot-external-right', toolheadIds: ['toolhead-right'], kind: 'fixed' },
            { sourceSlotId: 'slot-a1', toolheadIds: [], kind: 'unknown' },
          ],
        },
      },
    ],
  };
}

async function mockFleet(page: Page, stale = false): Promise<void> {
  await page.route('**/api/v1/fleet', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(topologyFleet(stale)) });
  });
  await page.route('**/api/v1/queue', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ apiVersion: '1', entries: [] }) });
  });
}

test('printer Materials renders typed material topology routes and unresolved state', async ({ page }) => {
  await mockFleet(page);
  await page.goto('/printers/topology-printer');
  await page.getByRole('button', { name: /^materials$/i }).click();

  const externalFeeds = page.locator('.material-external-section');
  const leftFeed = externalFeeds.locator('.external-feed-panel').filter({ hasText: 'External Left' });
  const rightFeed = externalFeeds.locator('.external-feed-panel').filter({ hasText: 'External Right' });
  await expect(leftFeed.locator('.material-slot-route')).toContainText('Fixed route');
  await expect(leftFeed.locator('.material-slot-route')).toContainText('Left toolhead');
  await expect(rightFeed.locator('.material-slot-route')).toContainText('Fixed route');
  await expect(rightFeed.locator('.material-slot-route')).toContainText('Right toolhead');

  const amsRoute = page.locator('.material-unit-panel').filter({ hasText: 'Material Unit' }).locator('.material-slot-route');
  await expect(amsRoute).toContainText('Unknown route');
  await expect(amsRoute).toContainText('No confirmed toolhead');
  await expect(amsRoute).toHaveClass(/warning/);

  const panel = page.locator('.material-topology-panel');
  await expect(panel).toBeVisible();
  await expect(panel).toContainText('Source routing');
  await expect(panel).toContainText('Routing current');
  await expect(panel).toContainText('External Left');
  await expect(panel).toContainText('Left toolhead');
  await expect(panel).toContainText('External Right');
  await expect(panel).toContainText('Right toolhead');
  await expect(panel).toContainText('Fixed route');
  await expect(panel).toContainText('A1');
  await expect(panel).toContainText('Unknown route');
  await expect(panel).toContainText('No confirmed toolhead');
  await expect(panel.locator('.material-topology-route')).toHaveCount(3);

  const genericCopy = await page.locator('.material-external-section, .material-topology-panel').allTextContents();
  expect(genericCopy.join(' ')).not.toContain('ams_mapping');
  expect(genericCopy.join(' ')).not.toContain('254');
  expect(genericCopy.join(' ')).not.toContain('255');
});

test('stale topology is visibly fail-closed as last-reported routing', async ({ page }) => {
  await mockFleet(page, true);
  await page.goto('/printers/topology-printer');
  await page.getByRole('button', { name: /^materials$/i }).click();

  const panel = page.locator('.material-topology-panel');
  await expect(panel).toHaveClass(/stale/);
  await expect(panel).toContainText('Routing data stale');
  await expect(panel).toContainText('These routes are the last report');
  await expect(page.locator('.material-slot-route.warning')).toHaveCount(3);
});

test('material topology remains contained on the phone viewport', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'phone');
  await mockFleet(page);
  await page.goto('/printers/topology-printer');
  await page.getByRole('button', { name: /^materials$/i }).click();

  const panel = page.locator('.material-topology-panel');
  await expect(panel).toBeVisible();
  const viewport = await page.evaluate(() => ({ width: window.innerWidth, scrollWidth: document.documentElement.scrollWidth }));
  expect(viewport.scrollWidth).toBeLessThanOrEqual(viewport.width + 1);

  const panelBox = await panel.boundingBox();
  expect(panelBox).not.toBeNull();
  expect(panelBox!.x).toBeGreaterThanOrEqual(-1);
  expect(panelBox!.x + panelBox!.width).toBeLessThanOrEqual(viewport.width + 1);
  for (const route of await panel.locator('.material-topology-route').all()) {
    const box = await route.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(-1);
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1);
  }
  for (const route of await page.locator('.material-slot-route').all()) {
    const box = await route.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(-1);
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1);
  }
});
