// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

export const bambuModelGroups = [
  { series: 'A1 Series', models: ['A1', 'A1 Mini'] },
  { series: 'A2 Series', models: ['A2L'] },
  { series: 'H2 Series', models: ['H2C', 'H2D', 'H2D Pro', 'H2S'] },
  { series: 'P Series', models: ['P1P', 'P1S', 'P2S'] },
  { series: 'X1 Series', models: ['X1', 'X1 Carbon', 'X1E'] },
  { series: 'X2 Series', models: ['X2D'] },
] as const;

const knownBambuModels = new Set<string>(bambuModelGroups.flatMap((group) => [...group.models]));

export function isKnownBambuModel(model: string): boolean {
  return knownBambuModels.has(model.trim());
}
