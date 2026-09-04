// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { chromium } from 'playwright';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, '..');
const outputDir = path.resolve(frontendDir, '..', 'docs', 'images', 'ui');
const baseUrl = process.env.FOXFORGE_SCREENSHOT_BASE_URL ?? 'http://127.0.0.1:4173';

await mkdir(outputDir, { recursive: true });

const browser = await chromium.launch({ headless: true });

async function capture({ route, file, width = 1600, height = 1000, fullPage = false }) {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    locale: 'en-US',
    colorScheme: 'dark',
    reducedMotion: 'reduce',
  });
  const page = await context.newPage();
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'networkidle' });
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
  });
  await page.screenshot({
    path: path.join(outputDir, file),
    fullPage,
    animations: 'disabled',
  });
  await context.close();
}

await capture({ route: '/?demo=1', file: 'overview.png' });
await capture({ route: '/printers?demo=1', file: 'printers.png' });
await capture({ route: '/printers/bambu-x2d-main?demo=1', file: 'printer-x2d.png', height: 1200 });
await capture({ route: '/inventory?demo=1', file: 'inventory.png', height: 1100 });
await capture({ route: '/queue?demo=1', file: 'queue.png' });
await capture({ route: '/farm?demo=1', file: 'farm.png' });
await capture({ route: '/?demo=1', file: 'overview-mobile.png', width: 430, height: 932, fullPage: true });

await browser.close();
