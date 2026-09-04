// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useTranslation } from 'react-i18next';

import type { PrinterViewModel } from '../../domain';

export interface FilamentPlanRow {
  rowId: string;
  slotId: string;
  estimatedMassG: string;
}

export interface FilamentPlanSubmission {
  materialBindings: Array<{ materialIndex: number; slotId: string }>;
  estimates: Array<{ materialIndex: number; estimatedMassG: string }>;
}

export function newFilamentPlanRow(): FilamentPlanRow {
  return { rowId: crypto.randomUUID(), slotId: '', estimatedMassG: '' };
}

export function buildFilamentPlan(rows: FilamentPlanRow[]): FilamentPlanSubmission | null {
  if (!rows.length) return null;
  const normalized = rows.map((row) => ({
    ...row,
    slotId: row.slotId.trim(),
    estimatedMassG: row.estimatedMassG.trim(),
  }));
  if (normalized.some((row) => !row.slotId || !positiveDecimal(row.estimatedMassG))) return null;
  return {
    materialBindings: normalized.map((row, materialIndex) => ({ materialIndex, slotId: row.slotId })),
    estimates: normalized.map((row, materialIndex) => ({
      materialIndex,
      estimatedMassG: row.estimatedMassG,
    })),
  };
}

export function FilamentPlanEditor({
  printer,
  rows,
  disabled,
  onChange,
}: {
  printer: PrinterViewModel | undefined;
  rows: FilamentPlanRow[];
  disabled: boolean;
  onChange: (rows: FilamentPlanRow[]) => void;
}) {
  const { t } = useTranslation();
  const slots = (printer?.materialSystem?.units ?? [])
    .flatMap((unit) => unit.slots.map((slot) => ({
      slotId: slot.slotId,
      label: slot.label || `${unit.label || unit.unitId} · ${slot.position + 1}`,
    })))
    .sort((left, right) => left.label.localeCompare(right.label));

  if (!printer) return null;
  if (!slots.length) {
    return <p className="filament-accounting-note warning-text">{t('filamentAccounting.noSlots')}</p>;
  }

  return (
    <fieldset className="filament-plan-editor" disabled={disabled}>
      <legend>{t('filamentAccounting.title')}</legend>
      <p>{t('filamentAccounting.text')}</p>
      <div className="filament-plan-rows">
        {rows.map((row, index) => (
          <div className="filament-plan-row" key={row.rowId}>
            <strong>{t('filamentAccounting.material', { index: index + 1 })}</strong>
            <label className="queue-command-field">
              <span>{t('filamentAccounting.slot')}</span>
              <select
                value={row.slotId}
                onChange={(event) => onChange(replaceRow(rows, index, { slotId: event.currentTarget.value }))}
              >
                <option value="">{t('filamentAccounting.chooseSlot')}</option>
                {slots.map((slot) => (
                  <option value={slot.slotId} key={slot.slotId}>{slot.label}</option>
                ))}
              </select>
            </label>
            <label className="queue-command-field">
              <span>{t('filamentAccounting.estimate')}</span>
              <input
                type="number"
                inputMode="decimal"
                min="0.001"
                step="0.001"
                value={row.estimatedMassG}
                onChange={(event) => onChange(replaceRow(rows, index, { estimatedMassG: event.currentTarget.value }))}
              />
              <small>{t('filamentAccounting.estimateHint')}</small>
            </label>
            {rows.length > 1 && (
              <button
                className="text-button"
                type="button"
                onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}
              >
                {t('filamentAccounting.removeMaterial')}
              </button>
            )}
          </div>
        ))}
      </div>
      <button
        className="secondary-button"
        type="button"
        onClick={() => onChange([...rows, newFilamentPlanRow()])}
      >
        {t('filamentAccounting.addMaterial')}
      </button>
    </fieldset>
  );
}

function replaceRow(
  rows: FilamentPlanRow[],
  index: number,
  patch: Partial<FilamentPlanRow>,
): FilamentPlanRow[] {
  return rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row));
}

function positiveDecimal(value: string): boolean {
  if (!value) return false;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0;
}
