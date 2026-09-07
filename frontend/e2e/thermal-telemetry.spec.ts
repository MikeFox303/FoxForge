// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test, type Page } from '@playwright/test';

const observedAt = '2026-09-08T00:00:00Z';

function thermalFleet(stale = false) {
  return {
    apiVersion: '1',
    printers: [{
      identity: {
        printerId: 'thermal-printer',
        displayName: 'Generic Thermal Printer',
        vendor: 'Example Vendor',
        model: 'Model Neutral',
        adapterKind: 'example',
      },
      snapshot: {
        printerId: 'thermal-printer',
        connection: 'connected',
        operationalState: 'idle',
        activeJob: null,
        observedAt,
        stale: false,
        faultSummary: [],
      },
      capabilities: [{
        capabilityId: 'foxforge.thermal_telemetry',
        majorVersion: 1,
        label: 'Thermal telemetry',
        reportsTargets: true,
      }],
      thermalTelemetry: {
        printerId: 'thermal-printer',
        observedAt,
        stale,
        zones: [
          { zoneId: 'hotend:0', kind: 'hotend', position: 0, label: 'Primary hotend', currentCelsius: 41, targetCelsius: 0 },
          { zoneId: 'bed:0', kind: 'bed', position: 10, currentCelsius: 59.5, targetCelsius: 60 },
          { zoneId: 'chamber:0', kind: 'chamber', position: 20, currentCelsius: 34 },
        ],
      },
    }],
  };
}

async function mockFleet(page: Page, stale = false): Promise<void> {
  await page.route('**/api/v1/fleet', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(thermalFleet(stale)) });
  });
  await page.route('**/api/v1/queue', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ apiVersion: '1', entries: [] }) });
  });
}

test('printer card and detail render common thermal telemetry without model inference', async ({ page }) => {
  await mockFleet(page);
  await page.goto('/printers');

  const card = page.locator('.printer-card').filter({ hasText: 'Generic Thermal Printer' });
  await expect(card).toBeVisible();
  await expect(card.locator('.thermal-strip')).toContainText('Primary hotend');
  await expect(card.locator('.thermal-strip')).toContainText('41°C');
  await expect(card.locator('.thermal-strip')).toContainText('59.5°C');

  await page.goto('/printers/thermal-printer');
  const panel = page.locator('.thermal-panel');
  await expect(panel).toBeVisible();
  await expect(panel).toContainText('Temperatures');
  await expect(panel).toContainText('Primary hotend');
  await expect(panel).toContainText('Bed');
  await expect(panel).toContainText('Chamber');
  await expect(panel).toContainText('60°C');

  const copy = await panel.textContent();
  expect(copy).not.toContain('X2D');
  expect(copy).not.toContain('nozzle_temper');
  expect(copy).not.toContain('device.extruder');
});

test('stale thermal telemetry remains visibly last-reported', async ({ page }) => {
  await mockFleet(page, true);
  await page.goto('/printers/thermal-printer');

  const panel = page.locator('.thermal-panel');
  await expect(panel).toHaveClass(/stale/);
  await expect(panel).toContainText('Last reported');
});

test('thermal operational surfaces do not overflow the phone viewport', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'phone');
  await mockFleet(page);
  await page.goto('/printers/thermal-printer');

  const panel = page.locator('.thermal-panel');
  await expect(panel).toBeVisible();
  const viewport = await page.evaluate(() => ({ width: window.innerWidth, scrollWidth: document.documentElement.scrollWidth }));
  expect(viewport.scrollWidth).toBeLessThanOrEqual(viewport.width + 1);

  const panelBox = await panel.boundingBox();
  expect(panelBox).not.toBeNull();
  expect(panelBox!.x).toBeGreaterThanOrEqual(-1);
  expect(panelBox!.x + panelBox!.width).toBeLessThanOrEqual(viewport.width + 1);
});
