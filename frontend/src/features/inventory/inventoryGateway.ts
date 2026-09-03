// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQuery } from '@tanstack/react-query';

import { inventoryData } from './mockInventory';
import type { InventoryData } from './types';

const inventoryQueryKey = ['inventory', 'spools'] as const;

async function loadInventory(): Promise<InventoryData> {
  // Temporary seam. A future REST client will map InventoryService DTOs here.
  return inventoryData;
}

export function useInventoryData(): InventoryData {
  const query = useQuery({
    queryKey: inventoryQueryKey,
    queryFn: loadInventory,
    initialData: inventoryData,
  });

  return query.data;
}
