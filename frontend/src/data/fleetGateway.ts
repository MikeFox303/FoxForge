// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQuery } from '@tanstack/react-query';

import type { FleetData } from '../domain';
import { fleetData } from '../mockData';

const fleetQueryKey = ['fleet', 'snapshot'] as const;

async function loadFleetSnapshot(): Promise<FleetData> {
  // Temporary seam: the public HTTP API will replace this in-memory gateway.
  return fleetData;
}

export function useFleetData(): FleetData {
  const query = useQuery({
    queryKey: fleetQueryKey,
    queryFn: loadFleetSnapshot,
    initialData: fleetData,
  });

  return query.data;
}
