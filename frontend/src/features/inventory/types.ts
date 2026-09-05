// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

export interface InventoryAssignmentView {
  printerId: string;
  slotId: string;
  assignedAt: string;
}

export interface SpoolInventoryView {
  spoolId: string;
  materialFamily: string;
  manufacturer?: string;
  productName?: string;
  rgbaHex?: string;
  initialFilamentMassG: string;
  remainingFilamentMassG: string;
  usedFilamentMassG: string;
  usedFraction: string;
  emptySpoolMassG?: string;
  purchaseDate?: string;
  archived: boolean;
  assignment?: InventoryAssignmentView;
}

export interface InventoryData {
  spools: SpoolInventoryView[];
  observedAt: string;
}

export type SpoolAdjustmentKind = 'consumption' | 'correction' | 'return' | 'waste';

export interface SpoolAdjustmentView {
  adjustmentId: string;
  kind: SpoolAdjustmentKind;
  deltaFilamentMassG: string;
  createdAt: string;
  note?: string;
}

export interface SpoolHistoryData {
  spoolId: string;
  adjustments: SpoolAdjustmentView[];
}
