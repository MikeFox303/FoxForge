// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { PrinterViewModel, ThermalZoneKind, ThermalZoneSnapshot } from '../../domain';

const kindOrder: Record<ThermalZoneKind, number> = {
  hotend: 0,
  bed: 1,
  chamber: 2,
  other: 3,
};

export interface ThermalPresentation {
  zones: ThermalZoneSnapshot[];
  stale: boolean;
}

export function thermalPresentation(
  printer: Pick<PrinterViewModel, 'thermalTelemetry'>,
  limit?: number,
): ThermalPresentation | undefined {
  const telemetry = printer.thermalTelemetry;
  if (!telemetry) return undefined;

  const zones = telemetry.zones
    .filter((zone) => zone.currentCelsius !== undefined || zone.targetCelsius !== undefined)
    .slice()
    .sort((left, right) => (
      kindOrder[left.kind] - kindOrder[right.kind]
      || left.position - right.position
      || left.zoneId.localeCompare(right.zoneId)
    ));

  return {
    zones: limit === undefined ? zones : zones.slice(0, Math.max(0, limit)),
    stale: telemetry.stale,
  };
}

export function temperatureLabel(value?: number): string {
  if (value === undefined || !Number.isFinite(value)) return '—';
  const rounded = Math.abs(value - Math.round(value)) < 0.05 ? Math.round(value) : Math.round(value * 10) / 10;
  return `${rounded}°C`;
}
