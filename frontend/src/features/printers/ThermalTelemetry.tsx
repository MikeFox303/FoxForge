// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useTranslation } from 'react-i18next';

import type { PrinterViewModel, ThermalZoneSnapshot } from '../../domain';
import { SectionHeading } from '../../ui/SectionHeading';
import { temperatureLabel, thermalPresentation } from './thermalPresentation';

export function ThermalTelemetryStrip({
  printer,
  limit,
}: {
  printer: Pick<PrinterViewModel, 'thermalTelemetry'>;
  limit?: number;
}) {
  const { t } = useTranslation();
  const presentation = thermalPresentation(printer, limit);
  if (!presentation || presentation.zones.length === 0) return null;

  return (
    <div className={`thermal-strip ${presentation.stale ? 'stale' : ''}`}>
      {presentation.zones.map((zone) => (
        <ThermalZoneCompact zone={zone} key={zone.zoneId} />
      ))}
      {presentation.stale && <span className="thermal-stale-badge">{t('thermalTelemetry.stale')}</span>}
    </div>
  );
}

export function ThermalTelemetryPanel({ printer }: { printer: Pick<PrinterViewModel, 'thermalTelemetry'> }) {
  const { t } = useTranslation();
  const presentation = thermalPresentation(printer);
  if (!presentation) return null;

  return (
    <section className={`panel thermal-panel ${presentation.stale ? 'stale' : ''}`}>
      <SectionHeading
        eyebrow={t('thermalTelemetry.eyebrow')}
        title={t('thermalTelemetry.title')}
        trailing={presentation.stale ? <span className="thermal-stale-badge">{t('thermalTelemetry.stale')}</span> : undefined}
        compact
      />
      {presentation.zones.length > 0 ? (
        <div className="thermal-zone-grid">
          {presentation.zones.map((zone) => <ThermalZoneCard zone={zone} key={zone.zoneId} />)}
        </div>
      ) : <div className="empty-state">{t('thermalTelemetry.noReading')}</div>}
    </section>
  );
}

function ThermalZoneCompact({ zone }: { zone: ThermalZoneSnapshot }) {
  const { t } = useTranslation();
  return (
    <div className="thermal-chip">
      <span>{zone.label ?? t(`thermalTelemetry.kinds.${zone.kind}`)}</span>
      <strong>{temperatureLabel(zone.currentCelsius)}</strong>
      {zone.targetCelsius !== undefined && <small>→ {temperatureLabel(zone.targetCelsius)}</small>}
    </div>
  );
}

function ThermalZoneCard({ zone }: { zone: ThermalZoneSnapshot }) {
  const { t } = useTranslation();
  const kindLabel = t(`thermalTelemetry.kinds.${zone.kind}`);
  return (
    <article className="thermal-zone-card">
      <div>
        <span>{zone.label ?? kindLabel}</span>
        {zone.label && <small>{kindLabel}</small>}
      </div>
      <div className="thermal-values">
        <div><span>{t('thermalTelemetry.current')}</span><strong>{temperatureLabel(zone.currentCelsius)}</strong></div>
        <div><span>{t('thermalTelemetry.target')}</span><strong>{temperatureLabel(zone.targetCelsius)}</strong></div>
      </div>
    </article>
  );
}
