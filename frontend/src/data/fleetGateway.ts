// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQuery } from '@tanstack/react-query';

import type { FleetData, QueueViewModel } from '../domain';
import { fleetData } from '../mockData';
import { demoModeEnabled, loadFleetFromApi, loadQueueFromApi } from './apiClient';

const fleetQueryKey = ['fleet', 'snapshot'] as const;
const queueQueryKey = ['queue', 'snapshot'] as const;
const emptyFleet: FleetData = { printers: [], queue: [] };
const emptyQueue: QueueViewModel[] = [];

export type FleetRuntimePhase = 'loading' | 'ready' | 'error';
export type FleetRuntimeTone = 'good' | 'warning' | 'danger';

export interface FleetRuntimeState {
  data: FleetData;
  phase: FleetRuntimePhase;
  isRefreshing: boolean;
  retry: () => void;
}

export interface QueryRuntimeState {
  isError: boolean;
  isPending: boolean;
  isPlaceholderData: boolean;
}

export function fleetRuntimePhase(state: QueryRuntimeState): FleetRuntimePhase {
  if (state.isError) return 'error';
  if (state.isPending || state.isPlaceholderData) return 'loading';
  return 'ready';
}

export function combinedFleetRuntimePhase(states: QueryRuntimeState[]): FleetRuntimePhase {
  if (states.some((state) => fleetRuntimePhase(state) === 'error')) return 'error';
  if (states.some((state) => fleetRuntimePhase(state) === 'loading')) return 'loading';
  return 'ready';
}

export function fleetRuntimeTone(phase: FleetRuntimePhase): FleetRuntimeTone {
  if (phase === 'error') return 'danger';
  if (phase === 'loading') return 'warning';
  return 'good';
}

async function loadFleetSnapshot(): Promise<FleetData> {
  return demoModeEnabled() ? fleetData : loadFleetFromApi();
}

async function loadQueueSnapshot(): Promise<QueueViewModel[]> {
  return demoModeEnabled() ? fleetData.queue : loadQueueFromApi();
}

export function useFleetData(): FleetRuntimeState {
  const demo = demoModeEnabled();
  const fleetQuery = useQuery({
    queryKey: [...fleetQueryKey, demo ? 'demo' : 'live'],
    queryFn: loadFleetSnapshot,
    initialData: demo ? fleetData : undefined,
    placeholderData: demo ? fleetData : emptyFleet,
    refetchInterval: demo ? false : 5_000,
  });
  const queueQuery = useQuery({
    queryKey: [...queueQueryKey, demo ? 'demo' : 'live'],
    queryFn: loadQueueSnapshot,
    initialData: demo ? fleetData.queue : undefined,
    placeholderData: demo ? fleetData.queue : emptyQueue,
    refetchInterval: demo ? false : 5_000,
  });

  const phase = combinedFleetRuntimePhase([fleetQuery, queueQuery]);
  return {
    data: {
      printers: (fleetQuery.data ?? emptyFleet).printers,
      queue: queueQuery.data ?? emptyQueue,
    },
    phase,
    isRefreshing: phase === 'ready' && (fleetQuery.isFetching || queueQuery.isFetching),
    retry: () => {
      void fleetQuery.refetch();
      void queueQuery.refetch();
    },
  };
}
