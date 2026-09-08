// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQuery } from '@tanstack/react-query';

import { demoModeEnabled } from '../../data/apiClient';
import {
  loadFilamentAccounting,
  type FilamentAccountingSnapshot,
} from './filamentAccountingClient';

export const filamentAccountingQueryKey = ['accounting'] as const;

const emptyAccounting: FilamentAccountingSnapshot = {
  apiVersion: '1',
  reservations: [],
  spools: [],
};

export type FilamentAccountingPhase = 'loading' | 'ready' | 'error';

export interface FilamentAccountingRuntimeState {
  data: FilamentAccountingSnapshot;
  phase: FilamentAccountingPhase;
  isRefreshing: boolean;
  retry: () => void;
}

export function filamentAccountingPhase(state: {
  isError: boolean;
  isPending: boolean;
  isPlaceholderData: boolean;
}): FilamentAccountingPhase {
  if (state.isError) return 'error';
  if (state.isPending || state.isPlaceholderData) return 'loading';
  return 'ready';
}

export function useFilamentAccounting(): FilamentAccountingRuntimeState {
  const demo = demoModeEnabled();
  const query = useQuery({
    queryKey: [...filamentAccountingQueryKey, demo ? 'demo' : 'live'],
    queryFn: async () => (demo ? emptyAccounting : loadFilamentAccounting()),
    initialData: demo ? emptyAccounting : undefined,
    placeholderData: emptyAccounting,
    refetchInterval: demo ? false : 10_000,
  });
  const phase = filamentAccountingPhase(query);
  return {
    data: query.data ?? emptyAccounting,
    phase,
    isRefreshing: phase === 'ready' && query.isFetching,
    retry: () => void query.refetch(),
  };
}
