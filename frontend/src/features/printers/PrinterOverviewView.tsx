// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useTranslation } from 'react-i18next';

import type { MaterialSlotSnapshot, PrinterViewModel, QueueViewModel } from '../../domain';
import { describeMaterialSource, printerStatusLabel } from '../../viewModel';
import { PrinterActiveJobPanel } from './PrinterActiveJobPanel';
import { summarizePrinterMaterials, type PrinterTelemetryPhase } from './printerDetailViewModel';
import { ThermalTelemetryPanel } from './ThermalTelemetry';

export function PrinterOverviewView({
  printer,
  queue,
  telemetryPhase,
}: {
  printer: PrinterViewModel;
  queue: QueueViewModel[];
  telemetryPhase: PrinterTelemetryPhase;
}) {
  const { t } = useTranslation();
  const job = printer.snapshot.activeJob;
  const materialSummary = summarizePrinterMaterials(printer);

  return (
    <div className="stack-lg">
      <section className="printer-detail-kpis">
        <DetailKpi label={t('printerDetail.connection')} value={t(`alpha.status.${printer.snapshot.connection}`)} />
        <DetailKpi label={t('printerDetail.state')} value={t(`alpha.status.${printerStatusLabel(printer)}`)} />
        <DetailKpi
          label={t('printerDetail.material')}
          value={describeMaterialSource(
            printer,
            t('printerDetail.noMaterialLoaded'),
            t('printerDetail.materialLoaded'),
          )}
        />
        <DetailKpi label={t('printerDetail.queue')} value={queue.length ? `${queue.length}` : t('printerDetail.clear')} />
      </section>

      <ThermalTelemetryPanel printer={printer} />

      {job ? (
        <PrinterActiveJobPanel printer={printer} />
      ) : (
        <section className="panel printer-ready-panel">
          <div className="ready-indicator">
            <span className={`status-dot ${telemetryPhase === 'live' ? 'good' : telemetryPhase === 'unavailable' ? 'danger' : 'warning'}`} />
          </div>
          <div>
            <h3>{telemetryPhase === 'live' ? t('printerDetail.ready') : t(`printerDetail.telemetry.${telemetryPhase}Title`)}</h3>
            <p>{telemetryPhase === 'live' ? t('printerDetail.readyText') : t(`printerDetail.telemetry.${telemetryPhase}Text`)}</p>
          </div>
        </section>
      )}

      <div className="two-column printer-detail-columns">
        <section className="panel">
          <div className="printer-section-heading compact-heading">
            <div><div className="eyebrow">{t('printerDetail.materialSystem')}</div><h3>{t('printerDetail.loadedMaterials')}</h3></div>
            <span>{materialSummary.loadedSlots}/{materialSummary.totalSlots}</span>
          </div>
          {printer.materialSystem ? (
            <div className="printer-material-summary-list">
              {printer.materialSystem.units.map((unit) => (
                <div className="printer-material-summary-row" key={unit.unitId}>
                  <div>
                    <strong>{unit.label ?? t(`alpha.materials.${materialUnitKey(unit.kind)}`)}</strong>
                    <span>{unit.slots.filter((slot) => slot.presence === 'loaded').length} {t('printerDetail.loaded').toLocaleLowerCase()}</span>
                  </div>
                  <div className="slot-dots">{unit.slots.map((slot) => <MaterialDot slot={slot} key={slot.slotId} />)}</div>
                </div>
              ))}
            </div>
          ) : <div className="empty-state">{t('printerDetail.noMaterialData')}</div>}
          {materialSummary.lowSlots > 0 && <div className="printer-inline-warning">{materialSummary.lowSlots} {t('printerDetail.lowMaterial')}</div>}
        </section>

        <section className="panel">
          <div className="printer-section-heading compact-heading">
            <div><div className="eyebrow">{t('printerDetail.nextWork')}</div><h3>{t('printerDetail.printerQueue')}</h3></div>
            <span>{queue.length}</span>
          </div>
          {queue.length ? (
            <div className="printer-queue-compact">
              {queue.slice(0, 4).map((entry) => (
                <div key={entry.queueId}>
                  <div><strong>{entry.requestedName}</strong><span>{entry.filename}</span></div>
                  <span className={`queue-badge state-${entry.state}`}>{t(`alpha.status.${entry.state}`)}</span>
                </div>
              ))}
            </div>
          ) : <div className="empty-state">{t('printerDetail.queueEmpty')}</div>}
        </section>
      </div>

      <section className="printer-capability-note">
        <div>
          <strong>{t('printerDetail.capabilityTitle')}</strong>
          <span>{t('printerDetail.capabilityText')}</span>
        </div>
      </section>
    </div>
  );
}

function DetailKpi({ label, value }: { label: string; value: string }) {
  return <article className="printer-detail-kpi"><span>{label}</span><strong>{value}</strong></article>;
}

function MaterialDot({ slot }: { slot: MaterialSlotSnapshot }) {
  const source = slot.detectedMaterial?.rgbaHex;
  const color = source?.length === 9 ? source.slice(0, 7) : source ?? '#475569';
  const low = (slot.detectedMaterial?.remainingFraction ?? 1) <= 0.2;
  return <span className={`material-dot ${slot.activity === 'active' ? 'active' : ''} ${low ? 'low' : ''}`} style={{ background: color }} />;
}

function materialUnitKey(kind: string): 'multiSlot' | 'external' | 'toolhead' | 'materialUnit' {
  if (kind === 'multi_slot') return 'multiSlot';
  if (kind === 'external') return 'external';
  if (kind === 'toolhead') return 'toolhead';
  return 'materialUnit';
}
