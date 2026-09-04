// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { expect, test, type Page } from '@playwright/test';

const operatorToken = process.env.FOXFORGE_E2E_COMMAND_TOKEN
  ?? 'foxforge-e2e-command-token-0123456789abcdef';

const observedAt = '2026-09-05T00:00:00Z';

function fleetResponse(displayName = 'Browser Test Printer') {
  return {
    apiVersion: '1',
    printers: [
      {
        identity: {
          printerId: 'browser-printer',
          displayName,
          vendor: 'test',
          model: 'E2E',
          serialNumber: 'E2E-001',
          adapterKind: 'fake',
        },
        snapshot: {
          printerId: 'browser-printer',
          connection: 'connected',
          operationalState: 'idle',
          activeJob: null,
          observedAt,
          stale: false,
          faultSummary: [],
        },
        capabilities: [
          { capabilityId: 'foxforge.print_execution', majorVersion: 1 },
        ],
      },
    ],
  };
}

async function unlockWrites(page: Page): Promise<void> {
  const access = page.locator('.operator-access-shell');
  await expect(access).toBeVisible();
  await access.locator('input[type="password"]').fill(operatorToken);
  await access.getByRole('button', { name: /unlock writes/i }).click();
  await expect(access).toContainText(/writes unlocked for this tab/i);
}

test('SPA routes and the single Add Printer entry point remain usable', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.app-shell')).toBeVisible();
  await expect(page.locator('.printer-setup-launcher')).toHaveCount(1);
  await expect(page.locator('.printer-setup-launcher')).toBeVisible();

  await page.goto('/printers');
  await expect(page.locator('.printer-setup-launcher')).toHaveCount(1);
  await expect(page.locator('.printer-setup-launcher')).toBeVisible();

  await page.locator('.printer-setup-launcher').click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeHidden();
});

test('operator write access is explicit and memory-only for the active tab', async ({ page }) => {
  await page.goto('/');
  await unlockWrites(page);

  const persistentCopy = await page.evaluate(() => ({
    local: Object.values(localStorage),
    session: Object.values(sessionStorage),
    url: location.href,
  }));
  expect(JSON.stringify(persistentCopy)).not.toContain(operatorToken);

  const access = page.locator('.operator-access-shell');
  await access.getByRole('button', { name: /^lock$/i }).click();
  await expect(access.locator('input[type="password"]')).toBeVisible();
});

test('queue workflow truthfully disables enqueue when no capable printer exists', async ({ page }) => {
  await page.goto('/queue');
  const panel = page.locator('.queue-command-panel');
  await expect(panel).toBeVisible();
  await expect(panel.locator('select option')).toHaveCount(1);
  await expect(panel.locator('.primary-button')).toBeDisabled();
  await expect(panel.locator('.queue-command-field').nth(1).locator('small')).not.toBeEmpty();
});

test('file selection, staging and enqueue keep one logical browser job', async ({ page }) => {
  let staged = false;
  let enqueued = false;

  await page.route('**/api/v1/fleet', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fleetResponse()) });
  });
  await page.route('**/api/v1/queue', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ apiVersion: '1', entries: [] }) });
      return;
    }
    enqueued = true;
    const payload = route.request().postDataJSON() as { queueId: string; printerId: string; artifactId: string };
    expect(payload.printerId).toBe('browser-printer');
    expect(payload.artifactId).toBe('sha256:browser-artifact');
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ queueId: payload.queueId, printerId: payload.printerId, state: 'pending' }),
    });
  });
  await page.route('**/api/v1/artifacts', async (route) => {
    staged = true;
    const headers = route.request().headers();
    expect(headers['x-foxforge-filename']).toContain('browser-test.gcode');
    expect(headers['x-foxforge-sha256']).toMatch(/^[0-9a-f]{64}$/);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        artifactId: 'sha256:browser-artifact',
        filename: 'browser-test.gcode',
        format: 'gcode',
        sizeBytes: 18,
        sha256: headers['x-foxforge-sha256'],
        replayed: false,
      }),
    });
  });

  await page.goto('/queue');
  await unlockWrites(page);
  const panel = page.locator('.queue-command-panel');
  await panel.locator('input[type="file"]').setInputFiles({
    name: 'browser-test.gcode',
    mimeType: 'text/plain',
    buffer: Buffer.from('G28\nG1 X10 Y10\nM84\n'),
  });
  await panel.locator('select').selectOption('browser-printer');
  await panel.locator('.primary-button').click();

  await expect.poll(() => staged).toBe(true);
  await expect.poll(() => enqueued).toBe(true);
  await expect(panel.locator('.queue-command-status')).toContainText(/queued/i);
  await expect(panel.locator('input[type="file"]')).toBeDisabled();
});

test('realtime resync invalidates canonical HTTP snapshots before polling fallback', async ({ page }) => {
  let fleetRequests = 0;

  await page.addInitScript(() => {
    class FakeEventSource {
      private readonly listeners = new Map<string, Set<EventListenerOrEventListenerObject>>();

      constructor(_url: string | URL) {
        (window as unknown as { __foxforgeE2EEventSource?: FakeEventSource }).__foxforgeE2EEventSource = this;
      }

      addEventListener(type: string, listener: EventListenerOrEventListenerObject | null): void {
        if (listener === null) return;
        const listeners = this.listeners.get(type) ?? new Set<EventListenerOrEventListenerObject>();
        listeners.add(listener);
        this.listeners.set(type, listeners);
      }

      removeEventListener(type: string, listener: EventListenerOrEventListenerObject | null): void {
        if (listener === null) return;
        this.listeners.get(type)?.delete(listener);
      }

      close(): void {}

      emit(type: string, data: string): void {
        const event = new MessageEvent(type, { data });
        for (const listener of this.listeners.get(type) ?? []) {
          if (typeof listener === 'function') listener.call(this, event);
          else listener.handleEvent(event);
        }
      }
    }

    Object.defineProperty(window, 'EventSource', {
      configurable: true,
      writable: true,
      value: FakeEventSource,
    });
  });

  await page.route('**/api/v1/fleet', async (route) => {
    fleetRequests += 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(fleetResponse(`Realtime Printer ${fleetRequests}`)),
    });
  });
  await page.route('**/api/v1/queue', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ apiVersion: '1', entries: [] }) });
  });

  await page.goto('/printers');
  await expect(page.getByText(/Realtime Printer \d+/)).toBeVisible();
  const baselineRequests = fleetRequests;

  const payload = JSON.stringify({
    apiVersion: '1',
    streamEpoch: '11111111-1111-4111-8111-111111111111',
    sequence: 0,
    emittedAt: observedAt,
  });
  await page.evaluate((eventPayload) => {
    const source = (window as unknown as {
      __foxforgeE2EEventSource?: { emit: (type: string, data: string) => void };
    }).__foxforgeE2EEventSource;
    if (!source) throw new Error('Realtime bridge did not create EventSource');
    source.emit('resync_required', eventPayload);
  }, payload);

  await expect.poll(() => fleetRequests, { timeout: 3_000 }).toBeGreaterThan(baselineRequests);
  await expect(page.getByText(new RegExp(`Realtime Printer ${fleetRequests}`))).toBeVisible();
});
