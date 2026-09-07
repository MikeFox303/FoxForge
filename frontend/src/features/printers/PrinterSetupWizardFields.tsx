// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type {
  BambuDiscoveryCandidate,
  PrinterSetupKind,
  PrinterSetupPayload,
} from '../../data/printerSetupClient';
import { bambuModelGroups } from './bambuModels';
import type { PrinterSetupWizardStep } from './printerSetupWizard';

type Labels = {
  bambu: string;
  moonraker: string;
  discovery: string;
  suggestedSubnets: string;
  refreshSubnets: string;
  loadingSubnets: string;
  noSuggestedSubnets: string;
  subnetHint: string;
  subnet: string;
  scanning: string;
  scan: string;
  candidateHint: string;
  noCandidates: string;
  useCandidate: string;
  host: string;
  accessCode: string;
  baseUrl: string;
  apiKey: string;
  displayName: string;
  model: string;
  modelPlaceholder: string;
  modelOther: string;
  modelCustom: string;
  serial: string;
  bambuIdentityHint: string;
  printerId: string;
  printerIdHint: string;
  vendor: string;
  kind: string;
  verified: string;
  verifyRequired: string;
};

type BusyState = {
  loadingSubnets: boolean;
  scanning: boolean;
  testing: boolean;
  saving: boolean;
};

type Values = {
  subnet: string;
  subnetSuggestions: readonly string[];
  scanAttempted: boolean;
  candidates: readonly BambuDiscoveryCandidate[];
  host: string;
  accessCode: string;
  baseUrl: string;
  apiKey: string;
  displayName: string;
  model: string;
  customBambuModel: boolean;
  serialNumber: string;
  printerId: string;
  vendor: string;
};

type Actions = {
  setKind: (kind: PrinterSetupKind) => void;
  refreshSubnets: () => void;
  setSubnet: (value: string) => void;
  scanBambu: () => void;
  useCandidate: (candidate: BambuDiscoveryCandidate) => void;
  setHost: (value: string) => void;
  setAccessCode: (value: string) => void;
  setBaseUrl: (value: string) => void;
  setApiKey: (value: string) => void;
  setDisplayName: (value: string) => void;
  setModelSelection: (value: string) => void;
  setModel: (value: string) => void;
  setSerialNumber: (value: string) => void;
  setPrinterId: (value: string) => void;
  setVendor: (value: string) => void;
};

export function PrinterSetupWizardFields({
  step,
  kind,
  labels,
  values,
  busy,
  payload,
  verified,
  actions,
}: {
  step: PrinterSetupWizardStep;
  kind: PrinterSetupKind;
  labels: Labels;
  values: Values;
  busy: BusyState;
  payload: PrinterSetupPayload;
  verified: boolean;
  actions: Actions;
}) {
  if (step === 'provider') {
    return <ProviderStep kind={kind} labels={labels} onKindChange={actions.setKind} />;
  }

  if (step === 'connection') {
    return kind === 'bambu'
      ? <BambuConnectionStep labels={labels} values={values} busy={busy} actions={actions} />
      : <MoonrakerConnectionStep labels={labels} values={values} actions={actions} />;
  }

  if (step === 'identity') {
    return kind === 'bambu'
      ? <BambuIdentityStep labels={labels} values={values} actions={actions} />
      : <MoonrakerIdentityStep labels={labels} values={values} actions={actions} />;
  }

  return <VerifyStep kind={kind} labels={labels} payload={payload} verified={verified} />;
}

function ProviderStep({
  kind,
  labels,
  onKindChange,
}: {
  kind: PrinterSetupKind;
  labels: Labels;
  onKindChange: (kind: PrinterSetupKind) => void;
}) {
  return (
    <div className="setup-provider-grid">
      <button
        className={`setup-provider-card ${kind === 'bambu' ? 'active' : ''}`}
        type="button"
        onClick={() => onKindChange('bambu')}
      >
        <span>Bambu</span><strong>{labels.bambu}</strong><small>MQTT · FTPS · AMS</small>
      </button>
      <button
        className={`setup-provider-card ${kind === 'moonraker' ? 'active' : ''}`}
        type="button"
        onClick={() => onKindChange('moonraker')}
      >
        <span>Klipper</span><strong>{labels.moonraker}</strong><small>Moonraker HTTP API</small>
      </button>
    </div>
  );
}

function BambuConnectionStep({
  labels,
  values,
  busy,
  actions,
}: {
  labels: Labels;
  values: Values;
  busy: BusyState;
  actions: Actions;
}) {
  const controlsBusy = busy.scanning || busy.testing || busy.saving;
  return (
    <>
      <div className="setup-message warning">
        <strong>{labels.discovery}</strong>
        <div className="setup-subnet-suggestions">
          <div className="setup-subnet-suggestions-head">
            <span>{labels.suggestedSubnets}</span>
            <button
              className="text-button"
              type="button"
              disabled={busy.loadingSubnets || controlsBusy}
              onClick={actions.refreshSubnets}
            >
              {busy.loadingSubnets ? labels.loadingSubnets : labels.refreshSubnets}
            </button>
          </div>
          {values.subnetSuggestions.length > 0 ? (
            <div className="setup-subnet-buttons">
              {values.subnetSuggestions.map((suggestion) => (
                <button
                  className={values.subnet === suggestion ? 'secondary-button active' : 'secondary-button'}
                  type="button"
                  key={suggestion}
                  onClick={() => actions.setSubnet(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          ) : !busy.loadingSubnets && <small>{labels.noSuggestedSubnets}</small>}
          <small>{labels.subnetHint}</small>
        </div>
        <div className="setup-form-row">
          <label>
            <span>{labels.subnet}</span>
            <input
              value={values.subnet}
              onChange={(event) => actions.setSubnet(event.target.value)}
              placeholder="192.168.1.0/24"
            />
          </label>
          <div className="setup-form-actions">
            <button
              className="secondary-button"
              type="button"
              disabled={controlsBusy || !values.subnet.trim()}
              onClick={actions.scanBambu}
            >
              {busy.scanning ? labels.scanning : labels.scan}
            </button>
          </div>
        </div>
        <small>{labels.candidateHint}</small>
        {values.scanAttempted && !busy.scanning && values.candidates.length === 0 && <span>{labels.noCandidates}</span>}
        {values.candidates.length > 0 && (
          <div className="configured-printers">
            {values.candidates.map((candidate) => (
              <article className="configured-printer" key={`${candidate.host}-${candidate.serialNumber ?? ''}`}>
                <div>
                  <strong>{candidate.displayName || candidate.model || candidate.host}</strong>
                  <span>{candidate.model || labels.bambu}</span>
                  <small>{candidate.host}{candidate.serialNumber ? ` · ${candidate.serialNumber}` : ''}</small>
                </div>
                <div className="configured-actions">
                  <button className="secondary-button" type="button" onClick={() => actions.useCandidate(candidate)}>
                    {labels.useCandidate}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
      <div className="setup-form-row">
        <label>
          <span>{labels.host}</span>
          <input value={values.host} onChange={(event) => actions.setHost(event.target.value)} required placeholder="192.168.1.50" />
        </label>
        <label>
          <span>{labels.accessCode}</span>
          <input value={values.accessCode} onChange={(event) => actions.setAccessCode(event.target.value)} required type="password" autoComplete="off" />
        </label>
      </div>
    </>
  );
}

function MoonrakerConnectionStep({ labels, values, actions }: { labels: Labels; values: Values; actions: Actions }) {
  return (
    <div className="setup-form-row">
      <label>
        <span>{labels.baseUrl}</span>
        <input value={values.baseUrl} onChange={(event) => actions.setBaseUrl(event.target.value)} required placeholder="http://192.168.1.100:7125" />
      </label>
      <label>
        <span>{labels.apiKey}</span>
        <input value={values.apiKey} onChange={(event) => actions.setApiKey(event.target.value)} type="password" autoComplete="off" />
      </label>
    </div>
  );
}

function BambuIdentityStep({ labels, values, actions }: { labels: Labels; values: Values; actions: Actions }) {
  return (
    <>
      <div className="setup-form-row">
        <label>
          <span>{labels.displayName}</span>
          <input value={values.displayName} onChange={(event) => actions.setDisplayName(event.target.value)} required />
        </label>
        <label>
          <span>{labels.model}</span>
          <select
            value={values.customBambuModel ? '__custom__' : values.model}
            onChange={(event) => actions.setModelSelection(event.target.value)}
          >
            <option value="">{labels.modelPlaceholder}</option>
            {bambuModelGroups.map((group) => (
              <optgroup key={group.series} label={group.series}>
                {group.models.map((bambuModel) => <option key={bambuModel} value={bambuModel}>{bambuModel}</option>)}
              </optgroup>
            ))}
            <option value="__custom__">{labels.modelOther}</option>
          </select>
          {values.customBambuModel && (
            <input value={values.model} onChange={(event) => actions.setModel(event.target.value)} placeholder={labels.modelCustom} />
          )}
        </label>
      </div>
      <label>
        <span>{labels.serial}</span>
        <input value={values.serialNumber} onChange={(event) => actions.setSerialNumber(event.target.value.toUpperCase())} required />
        <small>{labels.bambuIdentityHint}</small>
      </label>
    </>
  );
}

function MoonrakerIdentityStep({ labels, values, actions }: { labels: Labels; values: Values; actions: Actions }) {
  return (
    <>
      <div className="setup-form-row">
        <label>
          <span>{labels.printerId}</span>
          <input value={values.printerId} onChange={(event) => actions.setPrinterId(event.target.value)} required pattern="[A-Za-z0-9._-]{1,64}" />
          <small>{labels.printerIdHint}</small>
        </label>
        <label>
          <span>{labels.displayName}</span>
          <input value={values.displayName} onChange={(event) => actions.setDisplayName(event.target.value)} required />
        </label>
      </div>
      <div className="setup-form-row">
        <label>
          <span>{labels.vendor}</span>
          <input value={values.vendor} onChange={(event) => actions.setVendor(event.target.value)} placeholder="Klipper" />
        </label>
        <label>
          <span>{labels.model}</span>
          <input value={values.model} onChange={(event) => actions.setModel(event.target.value)} placeholder="Ender-3 V3 KE" />
        </label>
      </div>
    </>
  );
}

function VerifyStep({
  kind,
  labels,
  payload,
  verified,
}: {
  kind: PrinterSetupKind;
  labels: Labels;
  payload: PrinterSetupPayload;
  verified: boolean;
}) {
  return (
    <>
      <div className="setup-review-grid">
        <div><span>{labels.kind}</span><strong>{kind === 'bambu' ? labels.bambu : labels.moonraker}</strong></div>
        <div><span>{labels.displayName}</span><strong>{payload.displayName}</strong></div>
        <div>
          <span>{kind === 'bambu' ? labels.host : labels.baseUrl}</span>
          <strong>{kind === 'bambu' ? payload.connection.host : payload.connection.baseUrl}</strong>
        </div>
        <div><span>{labels.model}</span><strong>{payload.model || '—'}</strong></div>
        <div>
          <span>{kind === 'bambu' ? labels.serial : labels.printerId}</span>
          <strong>{kind === 'bambu' ? payload.serialNumber : payload.printerId}</strong>
        </div>
      </div>
      <div className={`setup-verification-state ${verified ? 'success' : 'pending'}`} role="status">
        <span className={`status-dot ${verified ? 'good' : 'warning'}`} aria-hidden="true" />
        <strong>{verified ? labels.verified : labels.verifyRequired}</strong>
      </div>
    </>
  );
}
