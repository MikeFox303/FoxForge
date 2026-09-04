// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { FleetData } from '../../domain';
import {
  addInventorySpool,
  correctSpoolRemaining,
  moveInventorySpool,
  setEmptySpoolMass,
  unassignInventorySpool,
} from './inventoryMutationClient';
import type { InventoryData, SpoolInventoryView } from './types';

export type InventoryMutationMode =
  | { kind: 'add' }
  | { kind: 'correct'; spool: SpoolInventoryView }
  | { kind: 'emptyMass'; spool: SpoolInventoryView }
  | { kind: 'move'; spool: SpoolInventoryView };

type Props = {
  mode: InventoryMutationMode | null;
  fleet: FleetData;
  inventory: InventoryData;
  onClose: () => void;
  onChanged: () => void;
};

const copy = {
  en: {
    addTitle: 'Add spool',
    addText: 'Create a FoxForge inventory spool. Mass values describe filament only, excluding the empty spool.',
    correctTitle: 'Correct remaining filament',
    correctText: 'Set the measured remaining filament. FoxForge records the difference as an immutable correction entry.',
    emptyTitle: 'Empty spool mass',
    emptyText: 'Store or update the tare mass for weighing this physical spool.',
    moveTitle: 'Move spool',
    moveText: 'Assign this spool to a material slot currently reported by a connected printer.',
    material: 'Material',
    manufacturer: 'Manufacturer',
    product: 'Product',
    color: 'Color',
    initial: 'Initial filament mass (g)',
    emptyMass: 'Empty spool mass (g)',
    purchase: 'Purchase date',
    remaining: 'Remaining filament (g)',
    note: 'Correction note',
    slot: 'Printer / material slot',
    unassigned: 'Unassigned',
    noSlots: 'No assignable material slots are currently reported by the fleet.',
    save: 'Save',
    saving: 'Saving…',
    cancel: 'Cancel',
    unassign: 'Remove assignment',
    required: 'Required',
  },
  ru: {
    addTitle: 'Добавить катушку',
    addText: 'Создайте катушку в учёте FoxForge. Масса относится только к филаменту, без веса пустой катушки.',
    correctTitle: 'Скорректировать остаток',
    correctText: 'Укажите измеренный остаток филамента. Разница сохранится как неизменяемая запись коррекции.',
    emptyTitle: 'Масса пустой катушки',
    emptyText: 'Сохраните или измените массу тары для взвешивания этой физической катушки.',
    moveTitle: 'Переместить катушку',
    moveText: 'Назначьте катушку слоту материала, который сейчас сообщает подключённый принтер.',
    material: 'Материал',
    manufacturer: 'Производитель',
    product: 'Продукт',
    color: 'Цвет',
    initial: 'Начальная масса филамента (г)',
    emptyMass: 'Масса пустой катушки (г)',
    purchase: 'Дата покупки',
    remaining: 'Остаток филамента (г)',
    note: 'Примечание к коррекции',
    slot: 'Принтер / слот материала',
    unassigned: 'Не назначена',
    noSlots: 'Сейчас ни один принтер не сообщает доступные слоты материала.',
    save: 'Сохранить',
    saving: 'Сохранение…',
    cancel: 'Отмена',
    unassign: 'Снять назначение',
    required: 'Обязательно',
  },
  uk: {
    addTitle: 'Додати котушку',
    addText: 'Створіть котушку в обліку FoxForge. Маса стосується лише філаменту, без ваги порожньої котушки.',
    correctTitle: 'Скоригувати залишок',
    correctText: 'Вкажіть виміряний залишок філаменту. Різниця збережеться як незмінний запис корекції.',
    emptyTitle: 'Маса порожньої котушки',
    emptyText: 'Збережіть або змініть масу тари для зважування цієї фізичної котушки.',
    moveTitle: 'Перемістити котушку',
    moveText: 'Призначте котушку слоту матеріалу, який зараз повідомляє підключений принтер.',
    material: 'Матеріал',
    manufacturer: 'Виробник',
    product: 'Продукт',
    color: 'Колір',
    initial: 'Початкова маса філаменту (г)',
    emptyMass: 'Маса порожньої котушки (г)',
    purchase: 'Дата покупки',
    remaining: 'Залишок філаменту (г)',
    note: 'Примітка до корекції',
    slot: 'Принтер / слот матеріалу',
    unassigned: 'Не призначена',
    noSlots: 'Зараз жоден принтер не повідомляє доступні слоти матеріалу.',
    save: 'Зберегти',
    saving: 'Збереження…',
    cancel: 'Скасувати',
    unassign: 'Зняти призначення',
    required: 'Обов’язково',
  },
} as const;

type Copy = { [K in keyof typeof copy.en]: string };

type SlotOption = {
  key: string;
  printerId: string;
  slotId: string;
  label: string;
};

export function InventoryMutationDialog({ mode, fleet, inventory, onClose, onChanged }: Props) {
  const { i18n } = useTranslation();
  const language = (i18n.resolvedLanguage ?? i18n.language).slice(0, 2) as keyof typeof copy;
  const c: Copy = copy[language] ?? copy.en;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [materialFamily, setMaterialFamily] = useState('');
  const [manufacturer, setManufacturer] = useState('');
  const [productName, setProductName] = useState('');
  const [rgbaHex, setRgbaHex] = useState('#FFFFFF');
  const [initialMass, setInitialMass] = useState('1000');
  const [emptyMass, setEmptyMass] = useState('');
  const [purchaseDate, setPurchaseDate] = useState('');
  const [remainingMass, setRemainingMass] = useState('');
  const [note, setNote] = useState('');
  const [slotKey, setSlotKey] = useState('');

  const spool = mode && mode.kind !== 'add' ? mode.spool : undefined;
  const slotOptions = useMemo(() => buildSlotOptions(fleet, inventory, spool), [fleet, inventory, spool]);

  useEffect(() => {
    setError(null);
    if (!mode) return;
    if (mode.kind === 'add') {
      setMaterialFamily('');
      setManufacturer('');
      setProductName('');
      setRgbaHex('#FFFFFF');
      setInitialMass('1000');
      setEmptyMass('');
      setPurchaseDate('');
      return;
    }
    if (mode.kind === 'correct') {
      setRemainingMass(mode.spool.remainingFilamentMassG);
      setNote('');
      return;
    }
    if (mode.kind === 'emptyMass') {
      setEmptyMass(mode.spool.emptySpoolMassG ?? '');
      return;
    }
    const current = mode.spool.assignment;
    setSlotKey(current ? slotIdentity(current.printerId, current.slotId) : '');
  }, [mode]);

  if (!mode) return null;

  const title = mode.kind === 'add'
    ? c.addTitle
    : mode.kind === 'correct'
      ? c.correctTitle
      : mode.kind === 'emptyMass'
        ? c.emptyTitle
        : c.moveTitle;
  const text = mode.kind === 'add'
    ? c.addText
    : mode.kind === 'correct'
      ? c.correctText
      : mode.kind === 'emptyMass'
        ? c.emptyText
        : c.moveText;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode.kind === 'add') {
        await addInventorySpool({
          materialFamily: materialFamily.trim(),
          manufacturer: manufacturer.trim() || undefined,
          productName: productName.trim() || undefined,
          rgbaHex: rgbaHex.trim() || undefined,
          initialFilamentMassG: initialMass.trim(),
          emptySpoolMassG: emptyMass.trim() || undefined,
          purchaseDate: purchaseDate || undefined,
        });
      } else if (mode.kind === 'correct') {
        await correctSpoolRemaining(mode.spool.spoolId, remainingMass.trim(), note);
      } else if (mode.kind === 'emptyMass') {
        await setEmptySpoolMass(mode.spool.spoolId, emptyMass);
      } else {
        const option = slotOptions.find((candidate) => candidate.key === slotKey);
        if (!option) throw new Error(c.noSlots);
        await moveInventorySpool(mode.spool.spoolId, option.printerId, option.slotId);
      }
      onChanged();
      onClose();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Inventory mutation failed.');
    } finally {
      setBusy(false);
    }
  };

  const unassign = async () => {
    if (!spool?.assignment) return;
    setBusy(true);
    setError(null);
    try {
      await unassignInventorySpool(spool.spoolId);
      onChanged();
      onClose();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Inventory mutation failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="inventory-dialog-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <form className="inventory-dialog" onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="inventory-dialog-title">
        <header>
          <div><h2 id="inventory-dialog-title">{title}</h2><p>{text}</p></div>
          <button type="button" className="secondary-button" onClick={onClose}>{c.cancel}</button>
        </header>

        {error && <div className="setup-message error" role="alert">{error}</div>}

        {mode.kind === 'add' && <div className="inventory-dialog-fields">
          <label><span>{c.material}</span><input value={materialFamily} onChange={(event) => setMaterialFamily(event.target.value)} required placeholder="PETG" /></label>
          <div className="inventory-dialog-row">
            <label><span>{c.manufacturer}</span><input value={manufacturer} onChange={(event) => setManufacturer(event.target.value)} placeholder="SUNLU" /></label>
            <label><span>{c.product}</span><input value={productName} onChange={(event) => setProductName(event.target.value)} placeholder="PETG" /></label>
          </div>
          <div className="inventory-dialog-row">
            <label><span>{c.initial}</span><input type="number" min="0.01" step="0.01" value={initialMass} onChange={(event) => setInitialMass(event.target.value)} required /></label>
            <label><span>{c.emptyMass}</span><input type="number" min="0" step="0.01" value={emptyMass} onChange={(event) => setEmptyMass(event.target.value)} /></label>
          </div>
          <div className="inventory-dialog-row">
            <label><span>{c.color}</span><input type="color" value={rgbaHex} onChange={(event) => setRgbaHex(event.target.value)} /></label>
            <label><span>{c.purchase}</span><input type="date" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} /></label>
          </div>
        </div>}

        {mode.kind === 'correct' && <div className="inventory-dialog-fields">
          <label><span>{c.remaining}</span><input type="number" min="0" step="0.01" max={mode.spool.initialFilamentMassG} value={remainingMass} onChange={(event) => setRemainingMass(event.target.value)} required /></label>
          <label><span>{c.note}</span><input value={note} onChange={(event) => setNote(event.target.value)} /></label>
        </div>}

        {mode.kind === 'emptyMass' && <div className="inventory-dialog-fields">
          <label><span>{c.emptyMass}</span><input type="number" min="0" step="0.01" value={emptyMass} onChange={(event) => setEmptyMass(event.target.value)} /></label>
        </div>}

        {mode.kind === 'move' && <div className="inventory-dialog-fields">
          {slotOptions.length ? <label><span>{c.slot}</span><select value={slotKey} onChange={(event) => setSlotKey(event.target.value)} required><option value="" disabled>{c.required}</option>{slotOptions.map((option) => <option value={option.key} key={option.key}>{option.label}</option>)}</select></label> : <div className="setup-message warning">{c.noSlots}</div>}
        </div>}

        <footer>
          {mode.kind === 'move' && spool?.assignment && <button type="button" className="text-button" disabled={busy} onClick={() => void unassign()}>{c.unassign}</button>}
          <button type="submit" className="primary-button" disabled={busy || (mode.kind === 'move' && slotOptions.length === 0)}>{busy ? c.saving : c.save}</button>
        </footer>
      </form>
    </div>
  );
}

function buildSlotOptions(fleet: FleetData, inventory: InventoryData, spool?: SpoolInventoryView): SlotOption[] {
  const occupiedByOther = new Set(
    inventory.spools
      .filter((candidate) => candidate.spoolId !== spool?.spoolId && candidate.assignment)
      .map((candidate) => slotIdentity(candidate.assignment!.printerId, candidate.assignment!.slotId)),
  );

  const options: SlotOption[] = [];
  for (const printer of fleet.printers) {
    for (const unit of printer.materialSystem?.units ?? []) {
      for (const slot of unit.slots) {
        const key = slotIdentity(printer.identity.printerId, slot.slotId);
        if (occupiedByOther.has(key)) continue;
        options.push({
          key,
          printerId: printer.identity.printerId,
          slotId: slot.slotId,
          label: `${printer.identity.displayName} · ${unit.label ?? unit.kind} · ${slot.label ?? `#${slot.position + 1}`}`,
        });
      }
    }
  }
  return options;
}

function slotIdentity(printerId: string, slotId: string): string {
  return `${printerId}\u0000${slotId}`;
}
