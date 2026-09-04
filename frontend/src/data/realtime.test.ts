// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { realtimeInvalidationKeys } from './realtime';

const payload = (topic: string) =>
  JSON.stringify({
    apiVersion: '1',
    streamEpoch: '00000000-0000-0000-0000-000000000001',
    sequence: 7,
    emittedAt: '2026-09-04T16:00:00Z',
    topic,
    change: 'changed',
  });

describe('realtimeInvalidationKeys', () => {
  it('routes fleet and printer configuration events to the fleet cache', () => {
    expect(realtimeInvalidationKeys('change', payload('fleet'))).toEqual([['fleet']]);
    expect(realtimeInvalidationKeys('change', payload('printer_configuration'))).toEqual([['fleet']]);
  });

  it('routes durable queue and inventory changes to their own cache families', () => {
    expect(realtimeInvalidationKeys('change', payload('queue'))).toEqual([['queue']]);
    expect(realtimeInvalidationKeys('change', payload('inventory'))).toEqual([['inventory']]);
  });

  it('fails closed to full snapshot resync for malformed or unknown events', () => {
    expect(realtimeInvalidationKeys('change', '{bad json')).toEqual([['fleet'], ['queue'], ['inventory']]);
    expect(realtimeInvalidationKeys('change', payload('future-topic'))).toEqual([
      ['fleet'],
      ['queue'],
      ['inventory'],
    ]);
  });

  it('invalidates every canonical snapshot when the server reports a replay gap', () => {
    expect(realtimeInvalidationKeys('resync_required', '{}')).toEqual([['fleet'], ['queue'], ['inventory']]);
  });
});
