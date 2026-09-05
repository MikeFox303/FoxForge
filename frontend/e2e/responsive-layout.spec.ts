// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test } from '@playwright/test';

const routes = [
  '/',
  '/printers',
  '/queue',
  '/materials',
  '/inventory',
  '/farm',
  '/system',
] as const;

const screenshotRoutes = new Set(['/', '/queue', '/inventory']);

function overlaps(a: { x: number; y: number; width: number; height: number }, b: { x: number; y: number; width: number; height: number }): boolean {
  return a.x < b.x + b.width
    && a.x + a.width > b.x
    && a.y < b.y + b.height
    && a.y + a.height > b.y;
}

for (const route of routes) {
  test(`responsive shell stays bounded on ${route}`, async ({ page }, testInfo) => {
    await page.goto(route);

    const shell = page.locator('.app-shell');
    const sidebar = page.locator('.sidebar');
    const topbar = page.locator('.topbar');
    const content = page.locator('.content');
    const addPrinter = page.locator('.printer-setup-launcher');
    const operatorShell = page.locator('.operator-access-shell');
    const operatorToggle = operatorShell.locator('.operator-access-toggle');
    const operatorInput = operatorShell.locator('input[type="password"]');

    await expect(shell).toBeVisible();
    await expect(sidebar).toBeVisible();
    await expect(topbar).toBeVisible();
    await expect(content).toBeVisible();
    await expect(addPrinter).toBeVisible();
    await expect(operatorToggle).toBeVisible();
    await expect(operatorInput).toBeHidden();

    const viewport = await page.evaluate(() => ({
      width: window.innerWidth,
      htmlScrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
    }));

    expect(viewport.htmlScrollWidth).toBeLessThanOrEqual(viewport.width + 1);
    expect(viewport.bodyScrollWidth).toBeLessThanOrEqual(viewport.width + 1);

    for (const locator of [shell, sidebar, topbar, content, addPrinter, operatorShell]) {
      const box = await locator.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.x).toBeGreaterThanOrEqual(-1);
      expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1);
    }

    const addPrinterBox = await addPrinter.boundingBox();
    const operatorBox = await operatorShell.boundingBox();
    expect(addPrinterBox).not.toBeNull();
    expect(operatorBox).not.toBeNull();
    expect(operatorBox!.height).toBeLessThanOrEqual(60);
    expect(overlaps(addPrinterBox!, operatorBox!)).toBe(false);

    if (testInfo.project.name === 'phone') {
      const sidebarBox = await sidebar.boundingBox();
      const topbarBox = await topbar.boundingBox();
      expect(sidebarBox).not.toBeNull();
      expect(topbarBox).not.toBeNull();
      expect(sidebarBox!.height).toBeLessThan(120);
      expect(topbarBox!.height).toBeLessThan(90);
    }

    if (testInfo.project.name === 'desktop-32-9') {
      const mainBox = await page.locator('.main-column').boundingBox();
      const contentBox = await content.boundingBox();
      expect(mainBox).not.toBeNull();
      expect(contentBox).not.toBeNull();
      expect(contentBox!.width).toBeLessThanOrEqual(1722);
      const leftGap = contentBox!.x - mainBox!.x;
      const rightGap = mainBox!.x + mainBox!.width - (contentBox!.x + contentBox!.width);
      expect(Math.abs(leftGap - rightGap)).toBeLessThanOrEqual(2);
    }

    if (screenshotRoutes.has(route) && testInfo.project.name !== 'tablet') {
      const safeRoute = route === '/' ? 'overview' : route.slice(1);
      await page.screenshot({
        path: testInfo.outputPath(`${testInfo.project.name}-${safeRoute}.png`),
        fullPage: false,
      });
    }
  });
}
