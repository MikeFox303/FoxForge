// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { demoModeEnabled } from './apiClient';

type ApplicationEventTopic = 'fleet' | 'queue' | 'inventory' | 'printer_configuration';

interface ApplicationEventPayload {
  apiVersion: '1';
  streamEpoch: string;
  sequence: number;
  emittedAt: string;
  topic?: ApplicationEventTopic;
  change?: string;
  resourceId?: string;
}

export type RealtimeQueryKey = readonly ['fleet'] | readonly ['queue'] | readonly ['inventory'];

const resyncKeys: readonly RealtimeQueryKey[] = [['fleet'], ['queue'], ['inventory']];

export function realtimeInvalidationKeys(
  eventType: 'change' | 'resync_required',
  rawData: string,
): readonly RealtimeQueryKey[] {
  if (eventType === 'resync_required') return resyncKeys;

  let payload: ApplicationEventPayload;
  try {
    payload = JSON.parse(rawData) as ApplicationEventPayload;
  } catch {
    return resyncKeys;
  }

  if (payload.apiVersion !== '1' || !Number.isInteger(payload.sequence) || !payload.streamEpoch) {
    return resyncKeys;
  }

  switch (payload.topic) {
    case 'fleet':
    case 'printer_configuration':
      return [['fleet']];
    case 'queue':
      return [['queue']];
    case 'inventory':
      return [['inventory']];
    default:
      return resyncKeys;
  }
}

export function RealtimeQueryBridge() {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (demoModeEnabled() || typeof EventSource === 'undefined') return undefined;

    const source = new EventSource('/api/v1/events');

    const invalidate = (eventType: 'change' | 'resync_required', rawData: string) => {
      for (const queryKey of realtimeInvalidationKeys(eventType, rawData)) {
        void queryClient.invalidateQueries({ queryKey });
      }
    };

    const onChange = (event: Event) => {
      const message = event as MessageEvent<string>;
      invalidate('change', message.data);
    };
    const onResyncRequired = (event: Event) => {
      const message = event as MessageEvent<string>;
      invalidate('resync_required', message.data);
    };

    source.addEventListener('change', onChange);
    source.addEventListener('resync_required', onResyncRequired);

    return () => {
      source.removeEventListener('change', onChange);
      source.removeEventListener('resync_required', onResyncRequired);
      source.close();
    };
  }, [queryClient]);

  return null;
}
