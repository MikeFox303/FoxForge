// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { inventoryRuntimePhase } from './inventoryGateway';

describe('inventory runtime state', () => {
  it('keeps placeholder inventory distinct from a successful empty response', () => {
    expect(inventoryRuntimePhase({ isError: false, isPending: false, isPlaceholderData: true })).toBe('loading');
    expect(inventoryRuntimePhase({ isError: false, isPending: false, isPlaceholderData: false })).toBe('ready');
  });

  it('surfaces query failures even while the initial request is pending', () => {
    expect(inventoryRuntimePhase({ isError: true, isPending: true, isPlaceholderData: true })).toBe('error');
  });
});
