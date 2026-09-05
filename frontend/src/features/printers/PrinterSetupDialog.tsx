// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { CommandAuthenticationRequiredError } from '../../data/commandClient';
import {
  addPrinter,
  discoverBambuPrinters,
  loadPrinterConfigurations,
  reconnectPrinter,
  removePrinter,
  testPrinterConnection,
  type BambuDiscoveryCandidate,
  type PrinterConfigurationView,
  type PrinterSetupKind,
  type PrinterSetupOutcome,
  type PrinterSetupPayload,
} from '../../data/printerSetupClient';
import { bambuModelGroups, isKnownBambuModel } from './bambuModels';
import { normalizeBambuSerial, stableBambuPrinterId } from './printerSetupIdentity';

type Props = {
  open: boolean;
  onClose: () => void;
  onChanged: () => void;
};

const copy = {
  en: {
    title: 'Printer connections',
    subtitle: 'Add Bambu LAN or Klipper/Moonraker printers directly from FoxForge.',
    configured: 'Configured printers',
    noConfigured: 'No printers are configured yet.',
    add: 'Add printer',
    kind: 'Connection type',
    bambu: 'Bambu Lab (LAN mode)',
    moonraker: 'Klipper / Moonraker',
    printerId: 'Printer ID',
    printerIdHint: 'Stable local ID, for example ender-ke.',
    bambuIdentityHint: 'FoxForge creates the stable local ID automatically from the Bambu serial number.',
    discovery: 'Find Bambu printers on the LAN',
    subnet: 'Subnet to scan',
    scan: 'Scan subnet',
    scanning: 'Scanning…',
    noCandidates: 'No Bambu candidates found. You can still enter the printer details manually.',
    candidateHint: 'Discovery is only a hint. FoxForge still verifies MQTT credentials before saving.',
    useCandidate: 'Use this printer',
    displayName: 'Display name',
    model: 'Model',
    modelPlaceholder: 'Select a model…',
    modelOther: 'Other / future model',
    modelCustom: 'Model name',
    vendor: 'Vendor',
    serial: 'Serial number',
    host: 'Printer IP / hostname',
    accessCode: 'LAN access code',
    baseUrl: 'Moonraker URL',
    apiKey: 'Moonraker API key (optional)',
    test: 'Test connection',
    testing: 'Testing…',
    save: 'Save and connect',
    saving: 'Saving…',
    reachable: 'Connection succeeded. FoxForge received a live printer state.',
    unreachable: 'Printer was not reachable',
    reconnect: 'Reconnect',
    reconnecting: 'Connecting…',
    remove: 'Delete',
    deleting: 'Deleting…',
    close: 'Close',
    refresh: 'Refresh',
    configuredSecret: 'credential saved',
    removeConfirm: 'Delete this printer from FoxForge? The physical printer is not modified.',
    deploymentError: 'Printer management is not enabled for this deployment. On Umbrel, update to a write-enabled FoxForge package and use the FoxForge app password in Operator access.',
    writesLocked: 'FoxForge write controls are locked. Open Operator access; on Umbrel use the FoxForge app password.',
    saveError: 'Unable to save printer.',
    deleteError: 'Unable to delete printer.',
  },
  ru: {
    title: 'Подключение принтеров',
    subtitle: 'Добавляйте Bambu LAN и Klipper/Moonraker прямо из FoxForge.',
    configured: 'Подключённые принтеры',
    noConfigured: 'Пока не настроено ни одного принтера.',
    add: 'Добавить принтер',
    kind: 'Тип подключения',
    bambu: 'Bambu Lab (LAN mode)',
    moonraker: 'Klipper / Moonraker',
    printerId: 'ID принтера',
    printerIdHint: 'Постоянный локальный ID, например ender-ke.',
    bambuIdentityHint: 'FoxForge автоматически создаёт постоянный локальный ID из серийного номера Bambu.',
    discovery: 'Найти принтеры Bambu в локальной сети',
    subnet: 'Подсеть для сканирования',
    scan: 'Сканировать подсеть',
    scanning: 'Сканирование…',
    noCandidates: 'Принтеры Bambu не найдены. Данные принтера можно ввести вручную.',
    candidateHint: 'Обнаружение только помогает заполнить форму. Перед сохранением FoxForge всё равно проверит MQTT и учётные данные.',
    useCandidate: 'Выбрать принтер',
    displayName: 'Название',
    model: 'Модель',
    modelPlaceholder: 'Выберите модель…',
    modelOther: 'Другая / будущая модель',
    modelCustom: 'Название модели',
    vendor: 'Производитель',
    serial: 'Серийный номер',
    host: 'IP / имя хоста принтера',
    accessCode: 'LAN access code',
    baseUrl: 'Адрес Moonraker',
    apiKey: 'API key Moonraker (необязательно)',
    test: 'Проверить подключение',
    testing: 'Проверка…',
    save: 'Сохранить и подключить',
    saving: 'Сохранение…',
    reachable: 'Подключение успешно. FoxForge получил актуальное состояние принтера.',
    unreachable: 'Не удалось подключиться к принтеру',
    reconnect: 'Переподключить',
    reconnecting: 'Подключение…',
    remove: 'Удалить',
    deleting: 'Удаление…',
    close: 'Закрыть',
    refresh: 'Обновить',
    configuredSecret: 'учётные данные сохранены',
    removeConfirm: 'Удалить этот принтер из FoxForge? Настройки физического принтера не изменятся.',
    deploymentError: 'Управление принтерами не включено в этой установке. В Umbrel обновите FoxForge до пакета с поддержкой записи и используйте пароль приложения FoxForge в разделе «Токен оператора».',
    writesLocked: 'Управление FoxForge заблокировано. Откройте «Токен оператора»; в Umbrel используйте пароль приложения FoxForge.',
    saveError: 'Не удалось сохранить принтер.',
    deleteError: 'Не удалось удалить принтер.',
  },
  uk: {
    title: 'Підключення принтерів',
    subtitle: 'Додавайте Bambu LAN і Klipper/Moonraker безпосередньо з FoxForge.',
    configured: 'Підключені принтери',
    noConfigured: 'Ще не налаштовано жодного принтера.',
    add: 'Додати принтер',
    kind: 'Тип підключення',
    bambu: 'Bambu Lab (LAN mode)',
    moonraker: 'Klipper / Moonraker',
    printerId: 'ID принтера',
    printerIdHint: 'Стабільний локальний ID, наприклад ender-ke.',
    bambuIdentityHint: 'FoxForge автоматично створює стабільний локальний ID із серійного номера Bambu.',
    discovery: 'Знайти принтери Bambu у локальній мережі',
    subnet: 'Підмережа для сканування',
    scan: 'Сканувати підмережу',
    scanning: 'Сканування…',
    noCandidates: 'Принтери Bambu не знайдено. Дані принтера можна ввести вручну.',
    candidateHint: 'Виявлення лише допомагає заповнити форму. Перед збереженням FoxForge все одно перевірить MQTT та облікові дані.',
    useCandidate: 'Вибрати принтер',
    displayName: 'Назва',
    model: 'Модель',
    modelPlaceholder: 'Виберіть модель…',
    modelOther: 'Інша / майбутня модель',
    modelCustom: 'Назва моделі',
    vendor: 'Виробник',
    serial: 'Серійний номер',
    host: 'IP / ім’я хоста принтера',
    accessCode: 'LAN access code',
    baseUrl: 'Адреса Moonraker',
    apiKey: 'API key Moonraker (необов’язково)',
    test: 'Перевірити підключення',
    testing: 'Перевірка…',
    save: 'Зберегти й підключити',
    saving: 'Збереження…',
    reachable: 'Підключення успішне. FoxForge отримав актуальний стан принтера.',
    unreachable: 'Не вдалося підключитися до принтера',
    reconnect: 'Перепідключити',
    reconnecting: 'Підключення…',
    remove: 'Видалити',
    deleting: 'Видалення…',
    close: 'Закрити',
    refresh: 'Оновити',
    configuredSecret: 'облікові дані збережені',
    removeConfirm: 'Видалити цей принтер із FoxForge? Налаштування фізичного принтера не зміняться.',
    deploymentError: 'Керування принтерами не ввімкнене в цій інсталяції. В Umbrel оновіть FoxForge до пакета з підтримкою запису та використовуйте пароль застосунку FoxForge у розділі «Токен оператора».',
    writesLocked: 'Керування FoxForge заблоковано. Відкрийте «Токен оператора»; в Umbrel використовуйте пароль застосунку FoxForge.',
    saveError: 'Не вдалося зберегти принтер.',
    deleteError: 'Не вдалося видалити принтер.',
  },
} as const;

type Copy = { [K in keyof typeof copy.en]: string };

export function PrinterSetupDialog({ open, onClose, onChanged }: Props) {
  const { i18n } = useTranslation();
  const language = (i18n.resolvedLanguage ?? i18n.language).slice(0, 2) as keyof typeof copy;
  const c: Copy = copy[language] ?? copy.en;
  const [configurations, setConfigurations] = useState<PrinterConfigurationView[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyPrinter, setBusyPrinter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<PrinterSetupOutcome | null>(null);
  const [kind, setKind] = useState<PrinterSetupKind>('bambu');
  const [printerId, setPrinterId] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [vendor, setVendor] = useState('');
  const [model, setModel] = useState('');
  const [customBambuModel, setCustomBambuModel] = useState(false);
  const [serialNumber, setSerialNumber] = useState('');
  const [host, setHost] = useState('');
  const [accessCode, setAccessCode] = useState('');
  const [baseUrl, setBaseUrl] = useState('http://');
  const [apiKey, setApiKey] = useState('');
  const [subnet, setSubnet] = useState('192.168.1.0/24');
  const [candidates, setCandidates] = useState<BambuDiscoveryCandidate[]>([]);
  const [scanAttempted, setScanAttempted] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  const errorMessage = (cause: unknown, fallback: string): string => {
    if (cause instanceof CommandAuthenticationRequiredError) return c.writesLocked;
    return cause instanceof Error ? cause.message : fallback;
  };

  const normalizedBambuSerial = normalizeBambuSerial(serialNumber);
  const payload = useMemo<PrinterSetupPayload>(() => ({
    printerId: kind === 'bambu' ? stableBambuPrinterId(normalizedBambuSerial) : printerId.trim(),
    displayName: displayName.trim(),
    kind,
    vendor: kind === 'bambu' ? 'Bambu Lab' : vendor.trim() || undefined,
    model: model.trim() || undefined,
    serialNumber: kind === 'bambu' ? normalizedBambuSerial || undefined : serialNumber.trim() || undefined,
    connection: kind === 'bambu'
      ? { host: host.trim(), accessCode: accessCode.trim() }
      : { baseUrl: baseUrl.trim(), apiKey: apiKey.trim() || undefined },
  }), [accessCode, apiKey, baseUrl, displayName, host, kind, model, normalizedBambuSerial, printerId, serialNumber, vendor]);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      setConfigurations(await loadPrinterConfigurations());
    } catch (cause) {
      const message = errorMessage(cause, c.deploymentError);
      setError(message.includes('Trusted browser') || message.includes('not enabled') ? c.deploymentError : message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) void refresh();
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  const scanBambu = async () => {
    if (!subnet.trim() || scanning) return;
    setScanning(true);
    setScanAttempted(true);
    setCandidates([]);
    setError(null);
    try {
      setCandidates(await discoverBambuPrinters(subnet.trim()));
    } catch (cause) {
      setError(errorMessage(cause, c.noCandidates));
    } finally {
      setScanning(false);
    }
  };

  const useCandidate = (candidate: BambuDiscoveryCandidate) => {
    setHost(candidate.host);
    if (candidate.serialNumber) setSerialNumber(candidate.serialNumber.toUpperCase());
    if (candidate.displayName) setDisplayName(candidate.displayName);
    if (candidate.model) {
      setModel(candidate.model);
      setCustomBambuModel(!isKnownBambuModel(candidate.model));
    }
    setOutcome(null);
    setError(null);
  };

  const testConnection = async () => {
    setTesting(true);
    setError(null);
    setOutcome(null);
    try {
      setOutcome(await testPrinterConnection(payload));
    } catch (cause) {
      setError(errorMessage(cause, c.unreachable));
    } finally {
      setTesting(false);
    }
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setOutcome(null);
    try {
      const result = await addPrinter(payload);
      setOutcome(result);
      await refresh();
      onChanged();
      setPrinterId('');
      setDisplayName('');
      setVendor('');
      setModel('');
      setCustomBambuModel(false);
      setSerialNumber('');
      setHost('');
      setAccessCode('');
      setApiKey('');
      setCandidates([]);
      setScanAttempted(false);
    } catch (cause) {
      setError(errorMessage(cause, c.saveError));
    } finally {
      setSaving(false);
    }
  };

  const reconnect = async (id: string) => {
    setBusyPrinter(id);
    setError(null);
    try {
      setOutcome(await reconnectPrinter(id));
      onChanged();
    } catch (cause) {
      setError(errorMessage(cause, c.unreachable));
    } finally {
      setBusyPrinter(null);
    }
  };

  const remove = async (id: string) => {
    if (!window.confirm(c.removeConfirm)) return;
    setBusyPrinter(id);
    setError(null);
    try {
      await removePrinter(id);
      await refresh();
      onChanged();
    } catch (cause) {
      setError(errorMessage(cause, c.deleteError));
    } finally {
      setBusyPrinter(null);
    }
  };

  return (
    <div className="setup-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="setup-dialog" role="dialog" aria-modal="true" aria-labelledby="printer-setup-title">
        <header className="setup-dialog-head">
          <div><h2 id="printer-setup-title">{c.title}</h2><p>{c.subtitle}</p></div>
          <button className="secondary-button" type="button" onClick={onClose}>{c.close}</button>
        </header>

        {error && <div className="setup-message error" role="alert">{error}</div>}
        {outcome && <div className={`setup-message ${outcome.reachable ? 'success' : 'warning'}`} role="status">
          <strong>{outcome.reachable ? c.reachable : c.unreachable}</strong>
          {!outcome.reachable && <span>{outcome.connectionError?.message ?? outcome.connection}</span>}
        </div>}

        <div className="setup-grid">
          <section className="setup-section">
            <div className="setup-section-head"><h3>{c.configured}</h3><button className="text-button" type="button" onClick={() => void refresh()}>{c.refresh}</button></div>
            {loading ? <div className="setup-placeholder">…</div> : configurations.length === 0 ? <div className="setup-placeholder">{c.noConfigured}</div> : (
              <div className="configured-printers">
                {configurations.map((printer) => (
                  <article className="configured-printer" key={printer.printerId}>
                    <div>
                      <strong>{printer.displayName}</strong>
                      <span>{printer.kind === 'bambu' ? c.bambu : c.moonraker}</span>
                      <small>{printer.kind === 'bambu' ? printer.connection.host : printer.connection.baseUrl}</small>
                      {(printer.connection.accessCodeConfigured || printer.connection.apiKeyConfigured) && <small>{c.configuredSecret}</small>}
                    </div>
                    <div className="configured-actions">
                      <button className="secondary-button" type="button" disabled={busyPrinter === printer.printerId} onClick={() => void reconnect(printer.printerId)}>{busyPrinter === printer.printerId ? c.reconnecting : c.reconnect}</button>
                      <button className="danger-button" type="button" disabled={busyPrinter === printer.printerId} onClick={() => void remove(printer.printerId)}>{busyPrinter === printer.printerId ? c.deleting : c.remove}</button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <form className="setup-section setup-form" onSubmit={save}>
            <h3>{c.add}</h3>
            <label><span>{c.kind}</span><select value={kind} onChange={(event) => setKind(event.target.value as PrinterSetupKind)}><option value="bambu">{c.bambu}</option><option value="moonraker">{c.moonraker}</option></select></label>
            {kind === 'bambu' ? <>
              <div className="setup-message warning">
                <strong>{c.discovery}</strong>
                <div className="setup-form-row">
                  <label><span>{c.subnet}</span><input value={subnet} onChange={(event) => setSubnet(event.target.value)} placeholder="192.168.1.0/24" /></label>
                  <div className="setup-form-actions"><button className="secondary-button" type="button" disabled={scanning || testing || saving || !subnet.trim()} onClick={() => void scanBambu()}>{scanning ? c.scanning : c.scan}</button></div>
                </div>
                <small>{c.candidateHint}</small>
                {scanAttempted && !scanning && candidates.length === 0 && <span>{c.noCandidates}</span>}
                {candidates.length > 0 && <div className="configured-printers">
                  {candidates.map((candidate) => (
                    <article className="configured-printer" key={`${candidate.host}-${candidate.serialNumber ?? ''}`}>
                      <div>
                        <strong>{candidate.displayName || candidate.model || candidate.host}</strong>
                        <span>{candidate.model || c.bambu}</span>
                        <small>{candidate.host}{candidate.serialNumber ? ` · ${candidate.serialNumber}` : ''}</small>
                      </div>
                      <div className="configured-actions"><button className="secondary-button" type="button" onClick={() => useCandidate(candidate)}>{c.useCandidate}</button></div>
                    </article>
                  ))}
                </div>}
              </div>
              <div className="setup-form-row">
                <label><span>{c.displayName}</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required /></label>
                <label>
                  <span>{c.model}</span>
                  <select
                    value={customBambuModel ? '__custom__' : model}
                    onChange={(event) => {
                      if (event.target.value === '__custom__') {
                        setCustomBambuModel(true);
                        setModel('');
                      } else {
                        setCustomBambuModel(false);
                        setModel(event.target.value);
                      }
                    }}
                  >
                    <option value="">{c.modelPlaceholder}</option>
                    {bambuModelGroups.map((group) => (
                      <optgroup key={group.series} label={group.series}>
                        {group.models.map((bambuModel) => <option key={bambuModel} value={bambuModel}>{bambuModel}</option>)}
                      </optgroup>
                    ))}
                    <option value="__custom__">{c.modelOther}</option>
                  </select>
                  {customBambuModel && <input value={model} onChange={(event) => setModel(event.target.value)} placeholder={c.modelCustom} />}
                </label>
              </div>
              <label><span>{c.serial}</span><input value={serialNumber} onChange={(event) => setSerialNumber(event.target.value.toUpperCase())} required /><small>{c.bambuIdentityHint}</small></label>
              <div className="setup-form-row"><label><span>{c.host}</span><input value={host} onChange={(event) => setHost(event.target.value)} required placeholder="192.168.1.50" /></label><label><span>{c.accessCode}</span><input value={accessCode} onChange={(event) => setAccessCode(event.target.value)} required type="password" autoComplete="off" /></label></div>
            </> : <>
              <div className="setup-form-row"><label><span>{c.printerId}</span><input value={printerId} onChange={(event) => setPrinterId(event.target.value)} required pattern="[A-Za-z0-9._-]{1,64}" /><small>{c.printerIdHint}</small></label><label><span>{c.displayName}</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required /></label></div>
              <div className="setup-form-row"><label><span>{c.vendor}</span><input value={vendor} onChange={(event) => setVendor(event.target.value)} placeholder="Klipper" /></label><label><span>{c.model}</span><input value={model} onChange={(event) => setModel(event.target.value)} placeholder="Ender-3 V3 KE" /></label></div>
              <div className="setup-form-row"><label><span>{c.baseUrl}</span><input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} required placeholder="http://192.168.1.100:7125" /></label><label><span>{c.apiKey}</span><input value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password" autoComplete="off" /></label></div>
            </>}
            <div className="setup-form-actions"><button className="secondary-button" type="button" disabled={testing || saving || scanning} onClick={() => void testConnection()}>{testing ? c.testing : c.test}</button><button className="primary-button" type="submit" disabled={testing || saving || scanning}>{saving ? c.saving : c.save}</button></div>
          </form>
        </div>
      </section>
    </div>
  );
}
