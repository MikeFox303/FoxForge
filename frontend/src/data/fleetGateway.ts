// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQuery } from '@tanstack/react-query';

import type { FleetData } from '../domain';
import { fleetData } from '../mockData';
import { demoModeEnabled, loadFleetFromApi } from './apiClient';

const fleetQueryKey = ['fleet', 'snapshot'] as const;
const emptyFleet: FleetData = { printers: [], queue: [] };

async function loadFleetSnapshot(): Promise<FleetData> {
  return demoModeEnabled() ? fleetData : loadFleetFromApi();
}

export function useFleetData(): FleetData {
  const demo = demoModeEnabled();
  const query = useQuery({
    queryKey: [...fleetQueryKey, demo ? 'demo' : 'live'],
    queryFn: loadFleetSnapshot,
    initialData: demo ? fleetData : undefined,
    placeholderData: demo ? fleetData : emptyFleet,
    refetchInterval: demo ? false : 5_000,
  });

  return query.data ?? emptyFleet;
}
