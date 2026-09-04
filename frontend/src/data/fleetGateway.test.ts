// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { fleetRuntimePhase } from './fleetGateway';

describe('fleet runtime feedback', () => {
  it('keeps the initial placeholder distinguishable from a real empty fleet', () => {
    expect(fleetRuntimePhase({ isError: false, isPending: false, isPlaceholderData: true })).toBe('loading');
    expect(fleetRuntimePhase({ isError: false, isPending: false, isPlaceholderData: false })).toBe('ready');
  });

  it('prioritizes an API failure over pending or placeholder state', () => {
    expect(fleetRuntimePhase({ isError: true, isPending: true, isPlaceholderData: true })).toBe('error');
  });
});
