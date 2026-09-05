// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test, type Page } from '@playwright/test';

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

test('operator access dropdown stays interactive and viewport-bound', async ({ page }, testInfo) => {
  test.skip(!['phone', 'desktop-16-9'].includes(testInfo.project.name));

  await page.goto('/');

  const topbar = page.locator('.topbar');
  const addPrinter = page.locator('.printer-setup-launcher');
  const operatorShell = page.locator('.operator-access-shell');
  const operatorToggle = operatorShell.locator('.operator-access-toggle');
  const operatorInput = operatorShell.locator('input[type="password"]');

  await expect(topbar).toBeVisible();
  await expect(addPrinter).toBeVisible();
  await expect(operatorToggle).toBeVisible();
  await expect(operatorInput).toBeHidden();
  await expect(operatorToggle).toHaveAttribute('aria-expanded', 'false');

  await operatorToggle.click();
  await expect(operatorToggle).toHaveAttribute('aria-expanded', 'true');
  await expect(operatorInput).toBeVisible();

  const dropdown = operatorShell.locator('.operator-access-frame.is-open .operator-access');
  await expect(dropdown).toBeVisible();
  await expectNoHorizontalViewportOverflow(page);

  const viewport = await page.evaluate(() => ({ width: window.innerWidth, height: window.innerHeight }));
  const topbarBox = await topbar.boundingBox();
  const addPrinterBox = await addPrinter.boundingBox();
  const dropdownBox = await dropdown.boundingBox();
  expect(topbarBox).not.toBeNull();
  expect(addPrinterBox).not.toBeNull();
  expect(dropdownBox).not.toBeNull();
  expect(topbarBox!.x).toBeGreaterThanOrEqual(-1);
  expect(topbarBox!.x + topbarBox!.width).toBeLessThanOrEqual(viewport.width + 1);
  expect(dropdownBox!.x).toBeGreaterThanOrEqual(-1);
  expect(dropdownBox!.y).toBeGreaterThanOrEqual(-1);
  expect(dropdownBox!.x + dropdownBox!.width).toBeLessThanOrEqual(viewport.width + 1);
  expect(dropdownBox!.y + dropdownBox!.height).toBeLessThanOrEqual(viewport.height + 1);
  expect(overlaps(addPrinterBox!, dropdownBox!)).toBe(false);

  const dropdownOwnsItsCenter = await page.evaluate(({ x, y }) => {
    const topElement = document.elementFromPoint(x, y);
    return Boolean(topElement?.closest('.operator-access-shell'));
  }, {
    x: dropdownBox!.x + dropdownBox!.width / 2,
    y: dropdownBox!.y + dropdownBox!.height / 2,
  });
  expect(dropdownOwnsItsCenter).toBe(true);

  await page.screenshot({
    path: testInfo.outputPath(`${testInfo.project.name}-operator-access-open.png`),
    fullPage: false,
  });

  await operatorToggle.click();
  await expect(operatorToggle).toHaveAttribute('aria-expanded', 'false');
  await expect(operatorInput).toBeHidden();
  await expectNoHorizontalViewportOverflow(page);

  const compactOperatorBox = await operatorShell.boundingBox();
  expect(compactOperatorBox).not.toBeNull();
  expect(compactOperatorBox!.height).toBeLessThanOrEqual(60);

  await addPrinter.click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeHidden();
});
