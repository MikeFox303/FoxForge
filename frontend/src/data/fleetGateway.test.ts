// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { combinedFleetRuntimePhase, fleetRuntimePhase } from './fleetGateway';

const ready = { isError: false, isPending: false, isPlaceholderData: false };
const loading = { isError: false, isPending: false, isPlaceholderData: true };
const failed = { isError: true, isPending: false, isPlaceholderData: false };

describe('fleet runtime feedback', () => {
  it('keeps the initial placeholder distinguishable from a real empty fleet', () => {
    expect(fleetRuntimePhase(loading)).toBe('loading');
    expect(fleetRuntimePhase(ready)).toBe('ready');
  });

  it('prioritizes an API failure over pending or placeholder state', () => {
    expect(fleetRuntimePhase({ isError: true, isPending: true, isPlaceholderData: true })).toBe('error');
  });

  it('treats fleet and queue reads as independent sources for the combined runtime state', () => {
    expect(combinedFleetRuntimePhase([ready, ready])).toBe('ready');
    expect(combinedFleetRuntimePhase([ready, loading])).toBe('loading');
    expect(combinedFleetRuntimePhase([ready, failed])).toBe('error');
    expect(combinedFleetRuntimePhase([failed, ready])).toBe('error');
  });
});
