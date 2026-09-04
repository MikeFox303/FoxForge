// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQuery } from '@tanstack/react-query';

import type { FleetData } from '../domain';
import { fleetData } from '../mockData';
import { demoModeEnabled, loadFleetFromApi } from './apiClient';

const fleetQueryKey = ['fleet', 'snapshot'] as const;
const emptyFleet: FleetData = { printers: [], queue: [] };

export type FleetRuntimePhase = 'loading' | 'ready' | 'error';
export type FleetRuntimeTone = 'good' | 'warning' | 'danger';

export interface FleetRuntimeState {
  data: FleetData;
  phase: FleetRuntimePhase;
  isRefreshing: boolean;
  retry: () => void;
}

export function fleetRuntimePhase(state: {
  isError: boolean;
  isPending: boolean;
  isPlaceholderData: boolean;
}): FleetRuntimePhase {
  if (state.isError) return 'error';
  if (state.isPending || state.isPlaceholderData) return 'loading';
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

export function useFleetData(): FleetRuntimeState {
  const demo = demoModeEnabled();
  const query = useQuery({
    queryKey: [...fleetQueryKey, demo ? 'demo' : 'live'],
    queryFn: loadFleetSnapshot,
    initialData: demo ? fleetData : undefined,
    placeholderData: demo ? fleetData : emptyFleet,
    refetchInterval: demo ? false : 5_000,
  });

  const phase = fleetRuntimePhase(query);
  return {
    data: query.data ?? emptyFleet,
    phase,
    isRefreshing: phase === 'ready' && query.isFetching,
    retry: () => void query.refetch(),
  };
}
