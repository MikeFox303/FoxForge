// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQuery } from '@tanstack/react-query';

import { demoModeEnabled, fetchJson } from '../../data/apiClient';
import { inventoryData } from './mockInventory';
import type { InventoryData, SpoolInventoryView } from './types';

const inventoryQueryKey = ['inventory', 'spools'] as const;
const emptyInventory: InventoryData = { spools: [], observedAt: new Date(0).toISOString() };

export type InventoryRuntimePhase = 'loading' | 'ready' | 'error';

export interface InventoryRuntimeState {
  data: InventoryData;
  phase: InventoryRuntimePhase;
  isRefreshing: boolean;
  retry: () => void;
}

export function inventoryRuntimePhase(state: {
  isError: boolean;
  isPending: boolean;
  isPlaceholderData: boolean;
}): InventoryRuntimePhase {
  if (state.isError) return 'error';
  if (state.isPending || state.isPlaceholderData) return 'loading';
  return 'ready';
}

interface ApiInventoryResponse {
  apiVersion: '1';
  spools: Array<{
    spoolId: string;
    materialFamily: string;
    manufacturer: string | null;
    productName: string | null;
    rgbaHex: string | null;
    initialFilamentMassG: string;
    remainingFilamentMassG: string;
    usedFilamentMassG: string;
    usedFraction: string;
    emptySpoolMassG: string | null;
    purchaseDate: string | null;
    archived: boolean;
    assignment: {
      printerId: string;
      slotId: string;
      assignedAt: string;
    } | null;
  }>;
}

async function loadInventory(): Promise<InventoryData> {
  if (demoModeEnabled()) {
    return inventoryData;
  }
  const payload = await fetchJson<ApiInventoryResponse>('/api/v1/inventory/spools');
  return {
    spools: payload.spools.map(mapSpool),
    observedAt: new Date().toISOString(),
  };
}

export function useInventoryData(): InventoryRuntimeState {
  const demo = demoModeEnabled();
  const query = useQuery({
    queryKey: [...inventoryQueryKey, demo ? 'demo' : 'live'],
    queryFn: loadInventory,
    initialData: demo ? inventoryData : undefined,
    placeholderData: demo ? inventoryData : emptyInventory,
    refetchInterval: demo ? false : 10_000,
  });

  const phase = inventoryRuntimePhase(query);
  return {
    data: query.data ?? emptyInventory,
    phase,
    isRefreshing: phase === 'ready' && query.isFetching,
    retry: () => void query.refetch(),
  };
}

function mapSpool(spool: ApiInventoryResponse['spools'][number]): SpoolInventoryView {
  return {
    spoolId: spool.spoolId,
    materialFamily: spool.materialFamily,
    manufacturer: spool.manufacturer ?? undefined,
    productName: spool.productName ?? undefined,
    rgbaHex: spool.rgbaHex ?? undefined,
    initialFilamentMassG: spool.initialFilamentMassG,
    remainingFilamentMassG: spool.remainingFilamentMassG,
    usedFilamentMassG: spool.usedFilamentMassG,
    usedFraction: spool.usedFraction,
    emptySpoolMassG: spool.emptySpoolMassG ?? undefined,
    purchaseDate: spool.purchaseDate ?? undefined,
    archived: spool.archived,
    assignment: spool.assignment ?? undefined,
  };
}
