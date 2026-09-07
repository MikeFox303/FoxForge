// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useTranslation } from 'react-i18next';

import type {
  MaterialRouteSnapshot,
  MaterialSlotSnapshot,
  MaterialUnitSnapshot,
  PrinterViewModel,
} from '../../domain';
import {
  groupMaterialUnits,
  materialRouteForSlot,
  resolveMaterialRoute,
  type MaterialRoutePresentation,
} from './materialPresentation';
import { materialSlots } from './printerDetailViewModel';

export function MaterialSystemView({ printer }: { printer: PrinterViewModel }) {
  const { t } = useTranslation();
  const units = printer.materialSystem?.units ?? [];
  const groups = groupMaterialUnits(units);

  if (!printer.materialSystem) {
    return (
      <>
        <div className="panel empty-state">{t('printerDetail.noMaterialData')}</div>
        <MaterialTopologyPanel printer={printer} />
      </>
    );
  }

  return (
    <>
      {groups.multiSlot.map((unit) => (
        <MaterialUnitPanel printer={printer} unit={unit} key={unit.unitId} />
      ))}

      {groups.external.length > 0 && (
        <section className="material-external-section">
          <div className="material-external-heading">
            <div>
              <div className="eyebrow">{t('printerDetail.materialSystem')}</div>
              <h3>{t('alpha.materials.external')}</h3>
            </div>
            <span className="count-pill">{t('alpha.materials.slotCount', { count: groups.external.length })}</span>
          </div>
          <div className="external-feed-grid">
            {groups.external.map((unit) => (
              <MaterialUnitPanel printer={printer} unit={unit} external key={unit.unitId} />
            ))}
          </div>
        </section>
      )}

      {groups.other.map((unit) => (
        <MaterialUnitPanel printer={printer} unit={unit} key={unit.unitId} />
      ))}
      <MaterialTopologyPanel printer={printer} />
    </>
  );
}

function MaterialUnitPanel({
  printer,
  unit,
  external = false,
}: {
  printer: PrinterViewModel;
  unit: MaterialUnitSnapshot;
  external?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <section className={`panel material-unit-panel ${external ? 'external-feed-panel' : ''}`}>
      <div className="material-unit-head">
        <div>
          <strong>{unit.label ?? t(`alpha.materials.${materialUnitKey(unit.kind)}`)}</strong>
          <span>{t(`alpha.materials.${materialUnitKey(unit.kind)}`)}</span>
        </div>
        <span className="count-pill">{t('alpha.materials.slotCount', { count: unit.slots.length })}</span>
      </div>
      <div className={`slot-grid printer-detail-slot-grid ${external ? 'external-feed-slots' : ''}`}>
        {unit.slots.map((slot) => <MaterialSlot printer={printer} slot={slot} key={slot.slotId} />)}
      </div>
    </section>
  );
}

function MaterialDot({ slot }: { slot: MaterialSlotSnapshot }) {
  const source = slot.detectedMaterial?.rgbaHex;
  const color = source?.length === 9 ? source.slice(0, 7) : source ?? '#475569';
  const low = (slot.detectedMaterial?.remainingFraction ?? 1) <= 0.2;
  return (
    <span
      className={`material-dot ${slot.activity === 'active' ? 'active' : ''} ${low ? 'low' : ''}`}
      style={{ background: color }}
    />
  );
}

function MaterialSlot({ printer, slot }: { printer: PrinterViewModel; slot: MaterialSlotSnapshot }) {
  const { t } = useTranslation();
  const material = slot.detectedMaterial;
  const fraction = material?.remainingFraction;
  const route = materialRouteForSlot(printer, slot.slotId);
  return (
    <article className={`material-slot printer-detail-slot ${slot.activity === 'active' ? 'active' : ''}`}>
      <div className="material-slot-head">
        <MaterialDot slot={slot} />
        <div>
          <strong>{slot.label ?? t('alpha.materials.slot', { number: slot.position + 1 })}</strong>
          <span>{slot.activity === 'active' ? t('printerDetail.activeSource') : t(`alpha.status.${slot.presence}`)}</span>
        </div>
      </div>
      {route && <MaterialRouteInline presentation={route} />}
      {material ? (
        <>
          <div className="material-name">
            {[material.vendorName, material.productName ?? material.materialFamily].filter(Boolean).join(' ')}
          </div>
          <div className="material-remaining">
            {fraction === undefined
              ? t('printerDetail.remainingUnknown')
              : `${Math.round(fraction * 100)}% ${t('printerDetail.remaining').toLocaleLowerCase()}`}
          </div>
          {fraction !== undefined && <Progress value={fraction} />}
        </>
      ) : <div className="empty-slot-label">{t('printerDetail.empty')}</div>}
    </article>
  );
}

function MaterialRouteInline({ presentation }: { presentation: MaterialRoutePresentation }) {
  const { t } = useTranslation();
  const { route, toolheads, unresolved, warning } = presentation;
  return (
    <div className={`material-slot-route ${warning ? 'warning' : ''}`}>
      <span className={`material-route-kind kind-${route.kind}`}>
        {t(`printerDetail.topology.routeKinds.${route.kind}`)}
      </span>
      <span className="material-slot-route-target">
        <span aria-hidden="true">→</span>
        {toolheads.length ? toolheads.map((toolhead) => (
          <strong key={toolhead.toolheadId}>
            {toolhead.label ?? t('printerDetail.topology.toolheadPosition', { position: toolhead.position + 1 })}
          </strong>
        )) : <strong>{t('printerDetail.topology.unresolved')}</strong>}
      </span>
      {unresolved && route.toolheadIds.length > 0 && (
        <small>{t('printerDetail.topology.incompleteTarget')}</small>
      )}
    </div>
  );
}

function MaterialTopologyPanel({ printer }: { printer: PrinterViewModel }) {
  const { t } = useTranslation();
  const topology = printer.materialTopology;
  if (!topology) {
    return (
      <section className="panel material-topology-panel">
        <div className="material-topology-head">
          <div>
            <div className="eyebrow">{t('printerDetail.topology.eyebrow')}</div>
            <h3>{t('printerDetail.topology.title')}</h3>
          </div>
        </div>
        <div className="empty-state material-topology-empty">{t('printerDetail.topology.noData')}</div>
      </section>
    );
  }

  const slots = materialSlots(printer);
  return (
    <section className={`panel material-topology-panel ${topology.stale ? 'stale' : ''}`}>
      <div className="material-topology-head">
        <div>
          <div className="eyebrow">{t('printerDetail.topology.eyebrow')}</div>
          <h3>{t('printerDetail.topology.title')}</h3>
          <p>{t('printerDetail.topology.text')}</p>
        </div>
        <span className={`material-topology-health ${topology.stale ? 'stale' : 'fresh'}`}>
          {t(`printerDetail.topology.${topology.stale ? 'stale' : 'fresh'}`)}
        </span>
      </div>
      {topology.stale && (
        <div className="material-topology-warning" role="status">{t('printerDetail.topology.staleText')}</div>
      )}
      {topology.routes.length ? (
        <div className="material-topology-grid">
          {topology.routes.map((route) => (
            <MaterialTopologyRoute
              key={route.sourceSlotId}
              printer={printer}
              route={route}
              sourceSlot={slots.find((slot) => slot.slotId === route.sourceSlotId)}
            />
          ))}
        </div>
      ) : <div className="empty-state material-topology-empty">{t('printerDetail.topology.noRoutes')}</div>}
    </section>
  );
}

function MaterialTopologyRoute({
  printer,
  route,
  sourceSlot,
}: {
  printer: PrinterViewModel;
  route: MaterialRouteSnapshot;
  sourceSlot?: MaterialSlotSnapshot;
}) {
  const { t } = useTranslation();
  const topology = printer.materialTopology;
  const material = sourceSlot?.detectedMaterial;
  if (!topology) return null;
  const presentation = resolveMaterialRoute(topology, route);

  return (
    <article className={`material-topology-route kind-${route.kind} ${presentation.warning ? 'warning' : ''}`}>
      <div className="material-topology-source">
        <span>{t('printerDetail.topology.source')}</span>
        <strong>{sourceSlot?.label ?? route.sourceSlotId}</strong>
        {material?.materialFamily && <small>{material.materialFamily}</small>}
      </div>
      <div className="material-topology-arrow" aria-hidden="true">→</div>
      <div className="material-topology-target">
        <span className={`material-route-kind kind-${route.kind}`}>
          {t(`printerDetail.topology.routeKinds.${route.kind}`)}
        </span>
        {presentation.toolheads.length ? presentation.toolheads.map((toolhead) => (
          <strong key={toolhead.toolheadId}>
            {toolhead.label ?? t('printerDetail.topology.toolheadPosition', { position: toolhead.position + 1 })}
          </strong>
        )) : <strong>{t('printerDetail.topology.unresolved')}</strong>}
        {presentation.unresolved && route.toolheadIds.length > 0 && (
          <small>{t('printerDetail.topology.incompleteTarget')}</small>
        )}
      </div>
    </article>
  );
}

function Progress({ value = 0 }: { value?: number }) {
  return (
    <div className="progress-track">
      <div className="progress-value" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} />
    </div>
  );
}

function materialUnitKey(kind: string): 'multiSlot' | 'external' | 'toolhead' | 'materialUnit' {
  if (kind === 'multi_slot') return 'multiSlot';
  if (kind === 'external') return 'external';
  if (kind === 'toolhead') return 'toolhead';
  return 'materialUnit';
}
