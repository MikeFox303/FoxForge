// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { CommandAuthenticationRequiredError } from '../../data/commandClient';
import {
  addPrinter,
  discoverBambuPrinters,
  loadBambuDiscoverySubnets,
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
import { isKnownBambuModel } from './bambuModels';
import { ConfiguredPrintersPanel } from './ConfiguredPrintersPanel';
import { PrinterSetupWizardFields } from './PrinterSetupWizardFields';
import { printerSetupCopy, type PrinterSetupCopy } from './printerSetupCopy';
import {
  setupCommandErrorMessage,
  setupOutcomeErrorMessage,
  type SetupLanguage,
} from './printerSetupErrors';
import { normalizeBambuSerial, stableBambuPrinterId } from './printerSetupIdentity';
import {
  canAdvancePrinterSetupStep,
  isPrinterSetupPayloadVerified,
  nextPrinterSetupStep,
  previousPrinterSetupStep,
  printerSetupPayloadFingerprint,
  printerSetupWizardSteps,
  type PrinterSetupWizardStep,
} from './printerSetupWizard';

type Props = {
  open: boolean;
  onClose: () => void;
  onChanged: () => void;
};

export function PrinterSetupDialog({ open, onClose, onChanged }: Props) {
  const { i18n } = useTranslation();
  const language = (i18n.resolvedLanguage ?? i18n.language).slice(0, 2) as SetupLanguage;
  const c: PrinterSetupCopy = printerSetupCopy[language] ?? printerSetupCopy.en;
  const [configurations, setConfigurations] = useState<PrinterConfigurationView[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyPrinter, setBusyPrinter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<PrinterSetupOutcome | null>(null);
  const [step, setStep] = useState<PrinterSetupWizardStep>('provider');
  const [verifiedFingerprint, setVerifiedFingerprint] = useState<string | null>(null);
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
  const [subnet, setSubnet] = useState('');
  const [subnetSuggestions, setSubnetSuggestions] = useState<string[]>([]);
  const [loadingSubnets, setLoadingSubnets] = useState(false);
  const [candidates, setCandidates] = useState<BambuDiscoveryCandidate[]>([]);
  const [scanAttempted, setScanAttempted] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  const errorMessage = (cause: unknown, fallback: string): string => {
    if (cause instanceof CommandAuthenticationRequiredError) return c.writesLocked;
    const connectionMessage = setupCommandErrorMessage(cause, language);
    if (connectionMessage) return connectionMessage;
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
  const payloadFingerprint = printerSetupPayloadFingerprint(payload);
  const verified = isPrinterSetupPayloadVerified(payload, verifiedFingerprint);

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

  const refreshSubnetSuggestions = async () => {
    if (loadingSubnets) return;
    setLoadingSubnets(true);
    try {
      const suggestions = await loadBambuDiscoverySubnets();
      setSubnetSuggestions(suggestions);
      setSubnet((current) => current || suggestions[0] || '');
    } catch (cause) {
      if (cause instanceof CommandAuthenticationRequiredError) setSubnetSuggestions([]);
    } finally {
      setLoadingSubnets(false);
    }
  };

  useEffect(() => {
    if (open) {
      setStep('provider');
      setVerifiedFingerprint(null);
      setOutcome(null);
      void refresh();
      void refreshSubnetSuggestions();
    }
  }, [open]);

  useEffect(() => {
    if (verifiedFingerprint !== null && verifiedFingerprint !== payloadFingerprint) {
      setVerifiedFingerprint(null);
      setOutcome(null);
    }
  }, [payloadFingerprint, verifiedFingerprint]);

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
    const testedFingerprint = payloadFingerprint;
    setTesting(true);
    setError(null);
    setOutcome(null);
    setVerifiedFingerprint(null);
    try {
      const result = await testPrinterConnection(payload);
      setOutcome(result);
      setVerifiedFingerprint(result.reachable ? testedFingerprint : null);
    } catch (cause) {
      setError(errorMessage(cause, c.unreachable));
    } finally {
      setTesting(false);
    }
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!verified) {
      setError(c.verifyRequired);
      return;
    }
    setSaving(true);
    setError(null);
    setOutcome(null);
    try {
      const result = await addPrinter(payload);
      setOutcome(result);
      await refresh();
      onChanged();
      resetDraft();
    } catch (cause) {
      setError(errorMessage(cause, c.saveError));
    } finally {
      setSaving(false);
    }
  };

  const resetDraft = () => {
    setPrinterId('');
    setDisplayName('');
    setVendor('');
    setModel('');
    setCustomBambuModel(false);
    setSerialNumber('');
    setHost('');
    setAccessCode('');
    setBaseUrl('http://');
    setApiKey('');
    setCandidates([]);
    setScanAttempted(false);
    setVerifiedFingerprint(null);
    setStep('provider');
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

  const stepLabel = (item: PrinterSetupWizardStep): string => {
    if (item === 'provider') return c.stepProvider;
    if (item === 'connection') return c.stepConnection;
    if (item === 'identity') return c.stepIdentity;
    return c.stepVerify;
  };
  const stepHint = step === 'provider'
    ? c.providerHint
    : step === 'connection'
      ? c.connectionHint
      : step === 'identity'
        ? c.identityHint
        : c.verifyHint;
  const currentStepIndex = printerSetupWizardSteps.indexOf(step);
  const canAdvance = canAdvancePrinterSetupStep(step, payload);
  const interactionBusy = testing || saving || scanning;

  const setModelSelection = (value: string) => {
    if (value === '__custom__') {
      setCustomBambuModel(true);
      setModel('');
      return;
    }
    setCustomBambuModel(false);
    setModel(value);
  };

  return (
    <div className="setup-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="setup-dialog" role="dialog" aria-modal="true" aria-labelledby="printer-setup-title">
        <header className="setup-dialog-head">
          <div><h2 id="printer-setup-title">{c.title}</h2><p>{c.subtitle}</p></div>
          <button className="secondary-button" type="button" onClick={onClose}>{c.close}</button>
        </header>

        {error && <div className="setup-message error" role="alert">{error}</div>}
        {outcome && (
          <div className={`setup-message ${outcome.reachable ? 'success' : 'warning'}`} role="status">
            <strong>{outcome.reachable ? c.reachable : c.unreachable}</strong>
            {!outcome.reachable && (
              <span>{outcome.connectionError ? setupOutcomeErrorMessage(outcome.connectionError, language) : outcome.connection}</span>
            )}
          </div>
        )}

        <div className="setup-grid">
          <ConfiguredPrintersPanel
            configurations={configurations}
            loading={loading}
            busyPrinter={busyPrinter}
            labels={c}
            onRefresh={() => void refresh()}
            onReconnect={(id) => void reconnect(id)}
            onRemove={(id) => void remove(id)}
          />

          <form className="setup-section setup-form setup-wizard" onSubmit={save}>
            <div className="setup-wizard-head">
              <div><h3>{c.add}</h3><p>{stepHint}</p></div>
              <span>{currentStepIndex + 1}/{printerSetupWizardSteps.length}</span>
            </div>
            <ol className="setup-wizard-steps" aria-label={c.add}>
              {printerSetupWizardSteps.map((item, index) => (
                <li
                  key={item}
                  className={`${item === step ? 'active' : ''} ${index < currentStepIndex ? 'complete' : ''}`}
                  aria-current={item === step ? 'step' : undefined}
                >
                  <span>{index + 1}</span><strong>{stepLabel(item)}</strong>
                </li>
              ))}
            </ol>

            <PrinterSetupWizardFields
              step={step}
              kind={kind}
              labels={c}
              values={{
                subnet,
                subnetSuggestions,
                scanAttempted,
                candidates,
                host,
                accessCode,
                baseUrl,
                apiKey,
                displayName,
                model,
                customBambuModel,
                serialNumber,
                printerId,
                vendor,
              }}
              busy={{ loadingSubnets, scanning, testing, saving }}
              payload={payload}
              verified={verified}
              actions={{
                setKind,
                refreshSubnets: () => void refreshSubnetSuggestions(),
                setSubnet,
                scanBambu: () => void scanBambu(),
                useCandidate,
                setHost,
                setAccessCode,
                setBaseUrl,
                setApiKey,
                setDisplayName,
                setModelSelection,
                setModel,
                setSerialNumber,
                setPrinterId,
                setVendor,
              }}
            />

            <div className="setup-form-actions setup-wizard-actions">
              {step !== 'provider' && (
                <button
                  className="secondary-button"
                  type="button"
                  disabled={interactionBusy}
                  onClick={() => setStep(previousPrinterSetupStep(step))}
                >
                  {c.back}
                </button>
              )}
              {step !== 'verify' ? (
                <button
                  className="primary-button"
                  type="button"
                  disabled={!canAdvance || interactionBusy}
                  onClick={() => { setError(null); setStep(nextPrinterSetupStep(step)); }}
                >
                  {c.next}
                </button>
              ) : (
                <>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={interactionBusy}
                    onClick={() => void testConnection()}
                  >
                    {testing ? c.testing : c.test}
                  </button>
                  <button className="primary-button" type="submit" disabled={!verified || interactionBusy}>
                    {saving ? c.saving : c.save}
                  </button>
                </>
              )}
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
