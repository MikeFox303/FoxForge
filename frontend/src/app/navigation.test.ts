// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { activeNavigationItem, navigation } from './navigation';

describe('app navigation', () => {
  it('keeps the approved seven top-level destinations in stable order', () => {
    expect(navigation.map((item) => item.key)).toEqual([
      'overview',
      'printers',
      'queue',
      'materials',
      'inventory',
      'farm',
      'system',
    ]);
  });

  it('resolves nested printer routes to the Printers workspace', () => {
    expect(activeNavigationItem('/printers/bambu-x2d-main').key).toBe('printers');
  });

  it('does not treat unrelated prefix collisions as active routes', () => {
    expect(activeNavigationItem('/printers-extra').key).toBe('overview');
  });

  it('falls back to Overview for unknown paths', () => {
    expect(activeNavigationItem('/not-a-route').key).toBe('overview');
  });
});
