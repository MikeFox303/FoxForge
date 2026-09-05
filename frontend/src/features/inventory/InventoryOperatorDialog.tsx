// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { FleetData } from '../../domain';
import {
  correctSpoolRemaining,
  createSpool,
  moveSpool,
  newInventoryCommandId,
  setEmptySpoolMass,
} from './inventoryCommandClient';
import { useSpoolHistory } from './inventoryGateway';
import type { SpoolInventoryView } from './types';

export type InventoryDialogAction = 'create' | 'correct' | 'move' | 'emptyMass' | 'history';

export function InventoryOperatorDialog({
  action,
  spool,
  fleet,
  onClose,
  onSuccess,
}: {
  action: InventoryDialogAction;
  spool?: SpoolInventoryView;
  fleet: FleetData;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [commandKey, setCommandKey] = useState(() => newInventoryCommandId(action));
  const [spoolId] = useState(() => crypto.randomUUID());
  const [materialFamily, setMaterialFamily] = useState('PLA');
  const [manufacturer, setManufacturer] = useState('');
  const [productName, setProductName] = useState('');
  const [color, setColor] = useState('#FFFFFF');
  const [initialMass, setInitialMass] = useState('1000');
  const [emptyMass, setEmptyMass] = useState(spool?.emptySpoolMassG ?? '');
  const [purchaseDate, setPurchaseDate] = useState('');
  const [remainingMass, setRemainingMass] = useState(spool?.remainingFilamentMassG ?? '');
  const [note, setNote] = useState('');
  const slots = useMemo(() => materialSlots(fleet), [fleet]);
  const [selectedSlot, setSelectedSlot] = useState(() => {
    if (!spool?.assignment) return '';
    return `${spool.assignment.printerId}\u0000${spool.assignment.slotId}`;
  });
  const history = useSpoolHistory(action === 'history' && spool ? spool.spoolId : null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [busy, onClose]);

  const payloadChanged = () => {
    setError(null);
    setCommandKey(newInventoryCommandId(action));
  };

  const submit = async () => {
    if (busy || action === 'history') return;
    setError(null);
    try {
      setBusy(true);
      if (action === 'create') {
        if (!positive(initialMass)) throw new Error(t('inventoryOperator.invalidPositiveMass'));
        if (emptyMass && !nonnegative(emptyMass)) throw new Error(t('inventoryOperator.invalidNonnegativeMass'));
        await createSpool({
          spoolId,
          materialFamily: materialFamily.trim(),
          manufacturer: optional(manufacturer),
          productName: optional(productName),
          rgbaHex: optional(color),
          initialFilamentMassG: initialMass.trim(),
          emptySpoolMassG: optional(emptyMass),
          purchaseDate: optional(purchaseDate),
        }, commandKey);
      } else if (action === 'correct' && spool) {
        if (!nonnegative(remainingMass)) throw new Error(t('inventoryOperator.invalidNonnegativeMass'));
        await correctSpoolRemaining(spool.spoolId, remainingMass.trim(), optional(note), commandKey);
      } else if (action === 'emptyMass' && spool) {
        if (emptyMass && !nonnegative(emptyMass)) throw new Error(t('inventoryOperator.invalidNonnegativeMass'));
        await setEmptySpoolMass(spool.spoolId, optional(emptyMass) ?? null, commandKey);
      } else if (action === 'move' && spool) {
        const [printerId, slotId] = selectedSlot.split('\u0000');
        if (!printerId || !slotId) throw new Error(t('inventoryOperator.selectSlot'));
        await moveSpool(spool.spoolId, printerId, slotId, commandKey);
      }
      onSuccess();
      onClose();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t('inventoryOperator.commandFailed'));
    } finally {
      setBusy(false);
    }
  };

  const title = action === 'create'
    ? t('inventoryOperator.createTitle')
    : action === 'correct'
      ? t('inventoryOperator.correctTitle')
      : action === 'move'
        ? t('inventoryOperator.moveTitle')
        : action === 'history'
          ? t('inventoryOperator.historyTitle')
          : t('inventoryOperator.editEmptyMass');

  return (
    <div className="setup-backdrop inventory-operator-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !busy) onClose();
    }}>
      <section className="setup-dialog inventory-operator-dialog" role="dialog" aria-modal="true" aria-label={title}>
        <div className="setup-dialog-head">
          <div><div className="eyebrow">{spool?.materialFamily ?? t('nav.inventory')}</div><h2>{title}</h2></div>
          <button className="text-button" type="button" onClick={onClose} disabled={busy}>{t('inventoryOperator.close')}</button>
        </div>

        {error && <div className="setup-message error" role="alert">{error}</div>}

        {action === 'create' && (
          <div className="setup-form">
            <div className="setup-form-row">
              <Field label={t('inventoryOperator.materialFamily')} value={materialFamily} required onChange={(value) => { setMaterialFamily(value); payloadChanged(); }} />
              <Field label={t('inventoryOperator.manufacturer')} value={manufacturer} onChange={(value) => { setManufacturer(value); payloadChanged(); }} />
            </div>
            <Field label={t('inventoryOperator.productName')} value={productName} onChange={(value) => { setProductName(value); payloadChanged(); }} />
            <div className="setup-form-row">
              <Field label={t('inventoryOperator.initialMass')} type="number" min="0.001" step="0.001" value={initialMass} required onChange={(value) => { setInitialMass(value); payloadChanged(); }} />
              <Field label={t('inventoryOperator.emptySpoolMass')} type="number" min="0" step="0.001" value={emptyMass} onChange={(value) => { setEmptyMass(value); payloadChanged(); }} />
            </div>
            <div className="setup-form-row">
              <Field label={t('inventoryOperator.color')} type="color" value={color} onChange={(value) => { setColor(value); payloadChanged(); }} />
              <Field label={t('inventoryOperator.purchaseDate')} type="date" value={purchaseDate} onChange={(value) => { setPurchaseDate(value); payloadChanged(); }} />
            </div>
          </div>
        )}

        {action === 'correct' && spool && (
          <div className="setup-form">
            <Field label={t('inventoryOperator.remainingMass')} type="number" min="0" step="0.001" value={remainingMass} required onChange={(value) => { setRemainingMass(value); payloadChanged(); }} />
            <Field label={t('inventoryOperator.note')} value={note} onChange={(value) => { setNote(value); payloadChanged(); }} />
          </div>
        )}

        {action === 'emptyMass' && spool && (
          <div className="setup-form">
            <Field label={t('inventoryOperator.emptySpoolMass')} type="number" min="0" step="0.001" value={emptyMass} onChange={(value) => { setEmptyMass(value); payloadChanged(); }} />
          </div>
        )}

        {action === 'move' && spool && (
          <div className="setup-form">
            <label>
              <span>{t('inventoryOperator.printerSlot')}</span>
              <select value={selectedSlot} onChange={(event) => { setSelectedSlot(event.currentTarget.value); payloadChanged(); }}>
                <option value="">{t('inventoryOperator.selectSlot')}</option>
                {slots.map((slot) => <option key={`${slot.printerId}:${slot.slotId}`} value={`${slot.printerId}\u0000${slot.slotId}`}>{slot.label}</option>)}
              </select>
            </label>
            {slots.length === 0 && <small className="warning-text">{t('inventoryOperator.noSlots')}</small>}
          </div>
        )}

        {action === 'history' && spool && (
          <div className="inventory-history-list">
            {history.isPending && <div className="inventory-refreshing" role="status">{t('inventory.refreshing')}</div>}
            {history.isError && <div className="setup-message error" role="alert">{t('inventory.errorText')}</div>}
            {history.data?.adjustments.length === 0 && <div className="setup-placeholder">{t('inventoryOperator.historyEmpty')}</div>}
            {history.data?.adjustments.map((item) => (
              <article className="inventory-history-item" key={item.adjustmentId}>
                <div><strong>{t(`inventoryOperator.kinds.${item.kind}`)}</strong><span>{new Date(item.createdAt).toLocaleString()}</span></div>
                <strong className={Number(item.deltaFilamentMassG) < 0 ? 'warning-text' : ''}>{signedMass(item.deltaFilamentMassG)}</strong>
                {item.note && <p>{item.note}</p>}
              </article>
            ))}
          </div>
        )}

        {action !== 'history' && (
          <div className="setup-form-actions">
            <button className="text-button" type="button" onClick={onClose} disabled={busy}>{t('inventoryOperator.cancel')}</button>
            <button className="primary-button" type="button" onClick={() => void submit()} disabled={busy || (action === 'move' && !selectedSlot)}>
              {busy ? t('inventoryOperator.saving') : action === 'create' ? t('inventoryOperator.create') : t('inventoryOperator.save')}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}

function Field({ label, value, onChange, type = 'text', required = false, min, step }: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  min?: string;
  step?: string;
}) {
  return <label><span>{label}</span><input type={type} value={value} required={required} min={min} step={step} onChange={(event) => onChange(event.currentTarget.value)} /></label>;
}

function materialSlots(fleet: FleetData) {
  return fleet.printers.flatMap((printer) => printer.materialSystem?.units.flatMap((unit) => unit.slots.map((slot) => ({
    printerId: printer.identity.printerId,
    slotId: slot.slotId,
    label: `${printer.identity.displayName} · ${unit.label ?? unit.unitId} · ${slot.label ?? slot.position + 1}`,
  }))) ?? []);
}

function optional(value: string): string | undefined {
  const normalized = value.trim();
  return normalized || undefined;
}

function positive(value: string): boolean {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0;
}

function nonnegative(value: string): boolean {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0;
}

function signedMass(value: string): string {
  const parsed = Number(value);
  return `${parsed > 0 ? '+' : ''}${value} g`;
}
