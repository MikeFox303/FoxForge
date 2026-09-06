// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test, type Page } from '@playwright/test';

type LanguageFixture = {
  language: 'ru' | 'uk';
  relative: RegExp;
  material: string;
  stale: string;
};

const fixtures: LanguageFixture[] = [
  {
    language: 'ru',
    relative: /8 мин назад/,
    material: 'Материал не загружен',
    stale: 'Данные устарели',
  },
  {
    language: 'uk',
    relative: /8 хв тому/,
    material: 'Матеріал не завантажено',
    stale: 'Дані застаріли',
  },
];

function localizedFleet() {
  return {
    apiVersion: '1',
    printers: [
      {
        identity: {
          printerId: 'localized-printer',
          displayName: 'Localized Printer',
          vendor: 'test',
          model: 'Locale',
          serialNumber: 'LOCALE-001',
          adapterKind: 'fake',
        },
        snapshot: {
          printerId: 'localized-printer',
          connection: 'connected',
          operationalState: 'idle',
          activeJob: null,
          observedAt: new Date(Date.now() - 8.5 * 60_000).toISOString(),
          stale: true,
          faultSummary: [],
        },
        capabilities: [
          { capabilityId: 'foxforge.print_execution', majorVersion: 1 },
        ],
      },
    ],
  };
}

async function mockReadModels(page: Page): Promise<void> {
  await page.route('**/api/v1/fleet', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(localizedFleet()),
    });
  });
  await page.route('**/api/v1/queue', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ apiVersion: '1', entries: [] }),
    });
  });
}

for (const fixture of fixtures) {
  test(`${fixture.language} printer detail has no English fallback at the target viewport`, async ({ page }) => {
    await page.addInitScript((language) => {
      window.localStorage.setItem('foxforge.language', language);
    }, fixture.language);
    await mockReadModels(page);
    await page.goto('/printers/localized-printer');

    const hero = page.locator('.printer-detail-hero');
    const kpis = page.locator('.printer-detail-kpis');
    await expect(hero).toBeVisible();
    await expect(kpis).toBeVisible();
    await expect(hero).toContainText(fixture.relative);
    await expect(hero).toContainText(fixture.stale);
    await expect(kpis).toContainText(fixture.material);
    await expect(hero).not.toContainText(/Updated/i);
    await expect(kpis).not.toContainText(/No material loaded/i);

    const viewport = await page.evaluate(() => ({
      width: window.innerWidth,
      htmlScrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
    }));
    expect(viewport.htmlScrollWidth).toBeLessThanOrEqual(viewport.width + 1);
    expect(viewport.bodyScrollWidth).toBeLessThanOrEqual(viewport.width + 1);

    for (const locator of [hero, kpis]) {
      const box = await locator.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.x).toBeGreaterThanOrEqual(-1);
      expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1);
    }
  });
}
