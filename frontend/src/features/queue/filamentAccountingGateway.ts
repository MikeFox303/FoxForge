// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQuery } from '@tanstack/react-query';

import { demoModeEnabled } from '../../data/apiClient';
import { loadFilamentAccounting, type FilamentAccountingSnapshot } from './filamentAccountingClient';

const emptyAccounting: FilamentAccountingSnapshot = {
  apiVersion: '1',
  reservations: [],
  spools: [],
};

export function useFilamentAccounting(): FilamentAccountingSnapshot {
  const demo = demoModeEnabled();
  const query = useQuery({
    queryKey: ['inventory', 'filament-accounting', demo ? 'demo' : 'live'],
    queryFn: loadFilamentAccounting,
    initialData: demo ? emptyAccounting : undefined,
    placeholderData: emptyAccounting,
    refetchInterval: demo ? false : 10_000,
  });
  return query.data ?? emptyAccounting;
}
