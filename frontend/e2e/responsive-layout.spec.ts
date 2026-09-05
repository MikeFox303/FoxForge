// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test, type Page } from '@playwright/test';

const routes = [
  '/',
  '/printers',
  '/queue',
  '/materials',
  '/inventory',
  '/farm',
  '/system',
] as const;

function overlaps(a: { x: number; y: number; width: number; height: number }, b: { x: number; y: number; width: number; height: number }): boolean {
  return a.x < b.x + b.width
    && a.x + a.width > b.x
    && a.y < b.y + b.height
    && a.y + a.height > b.y;
}

async function expectNoHorizontalViewportOverflow(page: Page): Promise<void> {
  const viewport = await page.evaluate(() => ({
    width: window.innerWidth,
    htmlScrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
  }));

  expect(viewport.htmlScrollWidth).toBeLessThanOrEqual(viewport.width + 1);
  expect(viewport.bodyScrollWidth).toBeLessThanOrEqual(viewport.width + 1);
}

function safeRouteName(route: typeof routes[number]): string {
  return route === '/' ? 'overview' : route.slice(1);
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

    await expectNoHorizontalViewportOverflow(page);
    const viewportWidth = await page.evaluate(() => window.innerWidth);

    for (const locator of [shell, sidebar, topbar, content, addPrinter, operatorShell]) {
      const box = await locator.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.x).toBeGreaterThanOrEqual(-1);
      expect(box!.x + box!.width).toBeLessThanOrEqual(viewportWidth + 1);
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

    await page.screenshot({
      path: testInfo.outputPath(`${testInfo.project.name}-${safeRouteName(route)}.png`),
      fullPage: false,
    });
  });
}

for (const language of ['ru', 'uk'] as const) {
  for (const route of routes) {
    test(`${language} copy stays bounded on ${route}`, async ({ page }, testInfo) => {
      test.skip(!['phone', 'desktop-16-9'].includes(testInfo.project.name));

      await page.addInitScript((selectedLanguage) => {
        window.localStorage.setItem('foxforge.language', selectedLanguage);
      }, language);
      await page.goto(route);

      const shell = page.locator('.app-shell');
      const sidebar = page.locator('.sidebar');
      const topbar = page.locator('.topbar');
      const content = page.locator('.content');
      const addPrinter = page.locator('.printer-setup-launcher');
      const operatorShell = page.locator('.operator-access-shell');

      for (const locator of [shell, sidebar, topbar, content, addPrinter, operatorShell]) {
        await expect(locator).toBeVisible();
      }

      await expectNoHorizontalViewportOverflow(page);
      const viewportWidth = await page.evaluate(() => window.innerWidth);
      for (const locator of [shell, sidebar, topbar, content, addPrinter, operatorShell]) {
        const box = await locator.boundingBox();
        expect(box).not.toBeNull();
        expect(box!.x).toBeGreaterThanOrEqual(-1);
        expect(box!.x + box!.width).toBeLessThanOrEqual(viewportWidth + 1);
      }

      await page.screenshot({
        path: testInfo.outputPath(`${testInfo.project.name}-${language}-${safeRouteName(route)}.png`),
        fullPage: false,
      });
    });
  }
}

test('printer setup modal owns the viewport and stays above global controls', async ({ page }, testInfo) => {
  await page.goto('/');

  const launcher = page.locator('.printer-setup-launcher');
  const backdrop = page.locator('.setup-backdrop');
  const dialog = page.locator('.setup-dialog');
  const operatorShell = page.locator('.operator-access-shell');

  await launcher.click();
  await expect(backdrop).toBeVisible();
  await expect(dialog).toBeVisible();

  expect(await backdrop.evaluate((element) => element.parentElement?.tagName)).toBe('BODY');
  expect(await page.evaluate(() => document.body.style.overflow)).toBe('hidden');

  const viewport = await page.evaluate(() => ({ width: window.innerWidth, height: window.innerHeight }));
  const backdropBox = await backdrop.boundingBox();
  const dialogBox = await dialog.boundingBox();
  expect(backdropBox).not.toBeNull();
  expect(dialogBox).not.toBeNull();
  expect(Math.abs(backdropBox!.x)).toBeLessThanOrEqual(1);
  expect(Math.abs(backdropBox!.y)).toBeLessThanOrEqual(1);
  expect(Math.abs(backdropBox!.width - viewport.width)).toBeLessThanOrEqual(1);
  expect(Math.abs(backdropBox!.height - viewport.height)).toBeLessThanOrEqual(1);
  expect(dialogBox!.x).toBeGreaterThanOrEqual(-1);
  expect(dialogBox!.y).toBeGreaterThanOrEqual(-1);
  expect(dialogBox!.x + dialogBox!.width).toBeLessThanOrEqual(viewport.width + 1);
  expect(dialogBox!.y + dialogBox!.height).toBeLessThanOrEqual(viewport.height + 1);

  const dialogAppearance = await dialog.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      backgroundColor: style.backgroundColor,
      borderTopWidth: style.borderTopWidth,
    };
  });
  expect(dialogAppearance.backgroundColor).not.toBe('rgba(0, 0, 0, 0)');
  expect(dialogAppearance.backgroundColor).not.toBe('transparent');
  expect(dialogAppearance.borderTopWidth).not.toBe('0px');

  const operatorBox = await operatorShell.boundingBox();
  expect(operatorBox).not.toBeNull();
  const operatorOwnsItsCenter = await page.evaluate(({ x, y }) => {
    const topElement = document.elementFromPoint(x, y);
    return Boolean(topElement?.closest('.operator-access-shell'));
  }, {
    x: operatorBox!.x + operatorBox!.width / 2,
    y: operatorBox!.y + operatorBox!.height / 2,
  });
  expect(operatorOwnsItsCenter).toBe(false);

  if (testInfo.project.name === 'phone') {
    expect(Math.abs(dialogBox!.x)).toBeLessThanOrEqual(1);
    expect(Math.abs(dialogBox!.y)).toBeLessThanOrEqual(1);
    expect(Math.abs(dialogBox!.width - viewport.width)).toBeLessThanOrEqual(1);
    expect(Math.abs(dialogBox!.height - viewport.height)).toBeLessThanOrEqual(1);
  }

  await page.screenshot({
    path: testInfo.outputPath(`${testInfo.project.name}-printer-setup-modal.png`),
    fullPage: false,
  });

  await page.keyboard.press('Escape');
  await expect(backdrop).toBeHidden();
  expect(await page.evaluate(() => document.body.style.overflow)).not.toBe('hidden');
});

for (const language of ['ru', 'uk'] as const) {
  test(`printer setup modal stays readable in ${language}`, async ({ page }, testInfo) => {
    test.skip(!['phone', 'desktop-16-9'].includes(testInfo.project.name));

    await page.addInitScript((selectedLanguage) => {
      window.localStorage.setItem('foxforge.language', selectedLanguage);
    }, language);
    await page.goto('/');
    await page.locator('.printer-setup-launcher').click();

    const dialog = page.locator('.setup-dialog');
    await expect(dialog).toBeVisible();
    const localizedLockedMessage = language === 'ru'
      ? 'Управление FoxForge заблокировано'
      : 'Керування FoxForge заблоковано';
    await expect(page.getByRole('alert')).toContainText(localizedLockedMessage);
    await expect(page.getByRole('alert')).not.toContainText('write controls are locked');
    await expectNoHorizontalViewportOverflow(page);

    const viewport = await page.evaluate(() => ({ width: window.innerWidth, height: window.innerHeight }));
    const dialogBox = await dialog.boundingBox();
    expect(dialogBox).not.toBeNull();
    expect(dialogBox!.x).toBeGreaterThanOrEqual(-1);
    expect(dialogBox!.y).toBeGreaterThanOrEqual(-1);
    expect(dialogBox!.x + dialogBox!.width).toBeLessThanOrEqual(viewport.width + 1);
    expect(dialogBox!.y + dialogBox!.height).toBeLessThanOrEqual(viewport.height + 1);

    await page.screenshot({
      path: testInfo.outputPath(`${testInfo.project.name}-${language}-printer-setup-modal.png`),
      fullPage: false,
    });
  });
}
