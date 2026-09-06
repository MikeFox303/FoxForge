// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { CommandApiError } from '../../data/commandClient';
import type { FleetData, PrinterViewModel, QueueViewModel } from '../../domain';
import '../../queue-command.css';
import {
  createQueueJobIdentity,
  dispatchPrintJob,
  enqueuePrintJob,
  inspectArtifactPrintPlan,
  reconcilePrintJob,
  sha256File,
  stagePrintArtifact,
  type ArtifactPrintPlan,
  type MaterialBindingIntent,
  type PrintPlanMaterialRequirement,
  type QueueCommandResult,
  type QueueJobIdentity,
  type StagedArtifact,
} from './queueCommandClient';
import {
  artifactFormatFromFilename,
  loadedMaterialSources,
  materialCompatibility,
  printerAcceptsFormat,
  requiresExplicitMaterialRouting,
  routePreview,
  routingReviewReady,
  selectedPlate,
} from './queueMaterialRouting';

type SubmitPhase =
  | 'idle'
  | 'hashing'
  | 'staging'
  | 'inspecting'
  | 'reviewing'
  | 'enqueuing'
  | 'queued'
  | 'dispatching'
  | 'blocked'
  | 'accepted'
  | 'indeterminate'
  | 'failed'
  | 'error';

interface PendingJob {
  identity: QueueJobIdentity;
  file: File;
  printerId: string;
  requestedName: string;
  sha256?: string;
  artifact?: StagedArtifact;
  printPlan?: ArtifactPrintPlan;
  plateIndex?: number;
  materialBindings: MaterialBindingIntent[];
  queue?: QueueCommandResult;
  dispatchIdempotencyKey?: string;
}

export function QueueCommandPanel({ fleet }: { fleet: FleetData }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const printers = useMemo(
    () => fleet.printers.filter((printer) => (
      printer.capabilities.some((item) => item.capabilityId === 'foxforge.print_execution' && item.majorVersion === 1)
    )),
    [fleet.printers],
  );
  const [file, setFile] = useState<File | null>(null);
  const [printerId, setPrinterId] = useState('');
  const [requestedName, setRequestedName] = useState('');
  const [pending, setPending] = useState<PendingJob | null>(null);
  const [phase, setPhase] = useState<SubmitPhase>('idle');
  const [error, setError] = useState<string | null>(null);

  const selectedPrinter = printers.find((printer) => printer.identity.printerId === printerId);
  const selectedFormat = file ? artifactFormatFromFilename(file.name) : undefined;
  const formatAccepted = selectedPrinter ? printerAcceptsFormat(selectedPrinter, selectedFormat) : false;
  const routingRequired = requiresExplicitMaterialRouting(selectedPrinter, selectedFormat);
  const routingReady = routingReviewReady({
    printer: selectedPrinter,
    plan: pending?.printPlan,
    plateIndex: pending?.plateIndex,
    bindings: pending?.materialBindings ?? [],
  });
  const currentPlate = selectedPlate(pending?.printPlan, pending?.plateIndex);
  const sources = loadedMaterialSources(selectedPrinter);
  const busy = ['hashing', 'staging', 'inspecting', 'enqueuing', 'dispatching'].includes(phase);
  const reviewRequiredBeforeEnqueue = routingRequired && !pending?.printPlan;
  const canPrepareOrEnqueue = Boolean(
    file
      && printerId
      && selectedFormat
      && formatAccepted
      && !busy
      && !pending?.queue
      && (!routingRequired || reviewRequiredBeforeEnqueue || routingReady),
  );
  const canDispatch = Boolean(
    pending?.queue
      && !busy
      && phase !== 'accepted'
      && phase !== 'indeterminate'
      && (phase !== 'failed' || pending.queue.error?.retryable === true),
  );

  const resetLogicalJob = () => {
    setPending(null);
    setPhase('idle');
    setError(null);
  };

  const onFileChange = (selected: File | null) => {
    setFile(selected);
    setRequestedName(selected ? stripKnownExtension(selected.name) : '');
    const nextFormat = selected ? artifactFormatFromFilename(selected.name) : undefined;
    if (printerId) {
      const currentPrinter = printers.find((printer) => printer.identity.printerId === printerId);
      if (!printerAcceptsFormat(currentPrinter, nextFormat)) setPrinterId('');
    }
    resetLogicalJob();
  };

  const onPrinterChange = (value: string) => {
    setPrinterId(value);
    resetLogicalJob();
  };

  const changePlate = (plateIndex: number | undefined) => {
    setPending((current) => current ? {
      ...current,
      identity: createQueueJobIdentity(),
      plateIndex,
      materialBindings: [],
      queue: undefined,
      dispatchIdempotencyKey: undefined,
    } : current);
    setPhase('reviewing');
    setError(null);
  };

  const changeBinding = (materialIndex: number, slotId: string) => {
    setPending((current) => {
      if (!current) return current;
      const remaining = current.materialBindings.filter((binding) => binding.materialIndex !== materialIndex);
      const materialBindings = slotId
        ? [...remaining, { materialIndex, slotId }].sort((left, right) => left.materialIndex - right.materialIndex)
        : remaining;
      return {
        ...current,
        identity: createQueueJobIdentity(),
        materialBindings,
        queue: undefined,
        dispatchIdempotencyKey: undefined,
      };
    });
    setPhase('reviewing');
    setError(null);
  };

  const addToQueue = async () => {
    if (!file || !printerId || !selectedPrinter || !selectedFormat || !formatAccepted) return;
    setError(null);
    const logicalJob = pending ?? {
      identity: createQueueJobIdentity(),
      file,
      printerId,
      requestedName: requestedName.trim(),
      materialBindings: [],
    };
    setPending(logicalJob);

    try {
      setPhase('hashing');
      const sha256 = logicalJob.sha256 ?? await sha256File(logicalJob.file);
      const withHash = { ...logicalJob, sha256 };
      setPending(withHash);

      setPhase('staging');
      const artifact = logicalJob.artifact ?? await stagePrintArtifact(logicalJob.file, sha256);
      let prepared: PendingJob = { ...withHash, artifact };
      setPending(prepared);

      if (requiresExplicitMaterialRouting(selectedPrinter, artifact.format)) {
        if (!prepared.printPlan) {
          setPhase('inspecting');
          const printPlan = await inspectArtifactPrintPlan(artifact.artifactId);
          const plateIndex = printPlan.plates.length === 1 ? printPlan.plates[0].plateIndex : undefined;
          prepared = { ...prepared, printPlan, plateIndex, materialBindings: [] };
          setPending(prepared);
          setPhase('reviewing');
          return;
        }
        if (!routingReviewReady({
          printer: selectedPrinter,
          plan: prepared.printPlan,
          plateIndex: prepared.plateIndex,
          bindings: prepared.materialBindings,
        })) {
          setPhase('reviewing');
          return;
        }
      }

      setPhase('enqueuing');
      const queue = await enqueuePrintJob({
        identity: prepared.identity,
        printerId: prepared.printerId,
        artifactId: artifact.artifactId,
        requestedName: prepared.requestedName,
        plateIndex: prepared.plateIndex,
        materialBindings: prepared.materialBindings.length ? prepared.materialBindings : undefined,
      });
      setPending({ ...prepared, queue });
      setPhase('queued');
      await refreshQueue(queryClient);
    } catch (cause) {
      setPhase('error');
      setError(errorMessage(cause));
    }
  };

  const dispatchQueuedJob = async () => {
    const logicalJob = pending;
    if (!logicalJob?.queue) return;
    setError(null);
    setPhase('dispatching');
    const idempotencyKey = logicalJob.dispatchIdempotencyKey ?? crypto.randomUUID();
    const attempt = { ...logicalJob, dispatchIdempotencyKey: idempotencyKey };
    setPending(attempt);

    try {
      const result = await dispatchPrintJob(logicalJob.queue.queueId, idempotencyKey);
      setPending({ ...attempt, queue: result, dispatchIdempotencyKey: undefined });
      setPhase(dispatchPhase(result));
      await refreshQueue(queryClient);
    } catch (cause) {
      setPending(attempt);
      if (isReconciliationError(cause)) {
        setPhase('indeterminate');
      } else {
        setPhase('error');
      }
      setError(errorMessage(cause));
      await refreshQueue(queryClient);
    }
  };

  return (
    <section className="panel queue-command-panel" aria-labelledby="queue-command-title">
      <div className="queue-command-heading">
        <div>
          <div className="eyebrow accent">{t('alpha.queueCommand.eyebrow')}</div>
          <h3 id="queue-command-title">{t('alpha.queueCommand.title')}</h3>
          <p>{t('alpha.queueCommand.text')}</p>
        </div>
        <span className="queue-command-safety">{t('alpha.queueCommand.safeBoundary')}</span>
      </div>

      <div className="queue-command-form">
        <label className="queue-command-field">
          <span>{t('alpha.queueCommand.file')}</span>
          <input
            type="file"
            accept=".gcode,.3mf"
            disabled={busy || Boolean(pending?.queue)}
            onChange={(event) => onFileChange(event.currentTarget.files?.[0] ?? null)}
          />
          <small>{file ? `${file.name} · ${formatBytes(file.size)}` : t('alpha.queueCommand.fileHint')}</small>
        </label>

        <label className="queue-command-field">
          <span>{t('alpha.queueCommand.printer')}</span>
          <select
            value={printerId}
            disabled={busy || Boolean(pending?.queue)}
            onChange={(event) => onPrinterChange(event.currentTarget.value)}
          >
            <option value="">{t('alpha.queueCommand.choosePrinter')}</option>
            {printers.map((printer) => (
              <option
                key={printer.identity.printerId}
                value={printer.identity.printerId}
                disabled={Boolean(selectedFormat) && !printerAcceptsFormat(printer, selectedFormat)}
              >
                {printer.identity.displayName}
              </option>
            ))}
          </select>
          <small>
            {selectedPrinter && selectedFormat && !formatAccepted
              ? t('queueRouting.formatUnsupported')
              : printers.length
                ? t('alpha.queueCommand.printerHint')
                : t('alpha.queueCommand.noCapablePrinter')}
          </small>
        </label>

        <label className="queue-command-field">
          <span>{t('alpha.queueCommand.name')}</span>
          <input
            value={requestedName}
            maxLength={256}
            disabled={busy || Boolean(pending?.queue)}
            placeholder={t('alpha.queueCommand.namePlaceholder')}
            onChange={(event) => {
              setRequestedName(event.currentTarget.value);
              resetLogicalJob();
            }}
          />
          <small>{t('alpha.queueCommand.nameHint')}</small>
        </label>
      </div>

      {routingRequired && pending?.printPlan && (
        <MaterialRoutingReview
          printer={selectedPrinter}
          plan={pending.printPlan}
          plateIndex={pending.plateIndex}
          bindings={pending.materialBindings}
          onPlateChange={changePlate}
          onBindingChange={changeBinding}
        />
      )}

      <div className="queue-command-status" role="status" aria-live="polite">
        <strong>{phaseLabel(phase, t)}</strong>
        <span>
          {phase === 'reviewing'
            ? t(routingReady ? 'queueRouting.reviewReady' : 'queueRouting.reviewBlocked')
            : phaseText(phase, t)}
        </span>
        {pending?.sha256 && <code title={pending.sha256}>{pending.sha256.slice(0, 12)}…</code>}
      </div>

      {error && (
        <div className="queue-command-error" role="alert">
          <strong>{t('alpha.queueCommand.requestFailed')}</strong>
          <span>{error}</span>
        </div>
      )}

      {phase === 'indeterminate' && (
        <div className="queue-command-indeterminate" role="alert">
          <strong>{t('alpha.queueCommand.indeterminateTitle')}</strong>
          <span>{t('alpha.queueCommand.indeterminateText')}</span>
        </div>
      )}

      <div className="queue-command-actions">
        {!pending?.queue && (
          <button
            className="primary-button"
            type="button"
            disabled={!canPrepareOrEnqueue}
            onClick={() => void addToQueue()}
          >
            {routingRequired && !pending?.printPlan
              ? t('queueRouting.inspect')
              : routingRequired
                ? t('queueRouting.addBoundJob')
                : phase === 'error'
                  ? t('alpha.queueCommand.retryAddRequest')
                  : t('alpha.queueCommand.addToQueue')}
          </button>
        )}
        {pending?.queue && canDispatch && (
          <button className="primary-button" type="button" disabled={busy} onClick={() => void dispatchQueuedJob()}>
            {dispatchButtonLabel(phase, t)}
          </button>
        )}
        {pending?.queue && (
          <button
            className="secondary-button"
            type="button"
            disabled={busy}
            onClick={() => {
              setFile(null);
              setPrinterId('');
              setRequestedName('');
              resetLogicalJob();
            }}
          >
            {t('alpha.queueCommand.newJob')}
          </button>
        )}
      </div>

      {phase === 'error' && pending?.queue && (
        <p className="queue-command-footnote">{t('alpha.queueCommand.sameDispatchIdentity')}</p>
      )}
    </section>
  );
}

function MaterialRoutingReview({
  printer,
  plan,
  plateIndex,
  bindings,
  onPlateChange,
  onBindingChange,
}: {
  printer: PrinterViewModel | undefined;
  plan: ArtifactPrintPlan;
  plateIndex: number | undefined;
  bindings: MaterialBindingIntent[];
  onPlateChange: (plateIndex: number | undefined) => void;
  onBindingChange: (materialIndex: number, slotId: string) => void;
}) {
  const { t } = useTranslation();
  const plate = selectedPlate(plan, plateIndex);
  const sources = loadedMaterialSources(printer);
  const missingSnapshots = !printer?.materialSystem || !printer.materialTopology;
  const staleSnapshots = Boolean(printer?.materialSystem?.stale || printer?.materialTopology?.stale);
  const relevantIssues = plan.issues.filter((issue) => issue.plateIndex === null || issue.plateIndex === plateIndex);

  return (
    <section className="queue-routing-review" aria-labelledby="queue-routing-review-title">
      <div className="queue-routing-heading">
        <div>
          <div className="eyebrow accent">{t('queueRouting.reviewTitle')}</div>
          <h4 id="queue-routing-review-title">{t('queueRouting.reviewTitle')}</h4>
          <p>{t('queueRouting.reviewText')}</p>
        </div>
        <span className="queue-routing-explicit">{t('alpha.queueCommand.safeBoundary')}</span>
      </div>

      {plan.plates.length > 1 && (
        <label className="queue-command-field queue-routing-plate">
          <span>{t('queueRouting.plate')}</span>
          <select
            value={plateIndex ?? ''}
            onChange={(event) => onPlateChange(event.currentTarget.value ? Number(event.currentTarget.value) : undefined)}
          >
            <option value="">{t('queueRouting.choosePlate')}</option>
            {plan.plates.map((candidate) => (
              <option key={candidate.plateIndex} value={candidate.plateIndex}>
                {t('queueRouting.plate')} {candidate.plateIndex}{candidate.readyForRouting ? '' : ' · blocked'}
              </option>
            ))}
          </select>
        </label>
      )}

      {!plan.readyForRouting && <RoutingAlert text={t('queueRouting.planBlocked')} />}
      {plate && !plate.readyForRouting && <RoutingAlert text={t('queueRouting.plateBlocked')} />}
      {missingSnapshots && <RoutingAlert text={t('queueRouting.systemMissing')} />}
      {staleSnapshots && <RoutingAlert text={t('queueRouting.systemStale')} />}
      {relevantIssues.map((issue, index) => (
        <RoutingAlert key={`${issue.code}-${issue.plateIndex ?? 'all'}-${index}`} text={t('queueRouting.planIssue', { message: issue.message })} />
      ))}

      {plate && (
        <div className="queue-routing-requirements">
          {plate.materialRequirements.map((requirement) => (
            <MaterialRequirementBinding
              key={requirement.materialIndex}
              printer={printer}
              requirement={requirement}
              slotId={bindings.find((binding) => binding.materialIndex === requirement.materialIndex)?.slotId ?? ''}
              sources={sources}
              onChange={(slotId) => onBindingChange(requirement.materialIndex, slotId)}
            />
          ))}
        </div>
      )}

      {plate && sources.length === 0 && <RoutingAlert text={t('queueRouting.noLoadedSources')} />}
      <div className={`queue-routing-gate ${routingReviewReady({ printer, plan, plateIndex, bindings }) ? 'ready' : 'blocked'}`}>
        {t(routingReviewReady({ printer, plan, plateIndex, bindings }) ? 'queueRouting.reviewReady' : 'queueRouting.reviewBlocked')}
      </div>
    </section>
  );
}

function MaterialRequirementBinding({
  printer,
  requirement,
  slotId,
  sources,
  onChange,
}: {
  printer: PrinterViewModel | undefined;
  requirement: PrintPlanMaterialRequirement;
  slotId: string;
  sources: ReturnType<typeof loadedMaterialSources>;
  onChange: (slotId: string) => void;
}) {
  const { t } = useTranslation();
  const selectedSource = sources.find((source) => source.slot.slotId === slotId);
  const compatibility = selectedSource ? materialCompatibility(requirement, selectedSource.slot) : undefined;
  const route = selectedSource ? routePreview(printer, requirement, selectedSource.slot.slotId) : undefined;

  return (
    <article className="queue-routing-requirement">
      <div className="queue-routing-requirement-head">
        <strong>{t('queueRouting.requirement', { index: requirement.materialIndex })}</strong>
        <div className="queue-routing-meta">
          <span>{t('queueRouting.material')}: {requirement.materialFamily ?? '—'}</span>
          {requirement.profileName && <span>{t('queueRouting.profile')}: {requirement.profileName}</span>}
          <span>
            {t('queueRouting.expectedToolhead')}: {requirement.expectedToolheadPosition ?? t('queueRouting.toolheadUnknown')}
          </span>
        </div>
      </div>

      <label className="queue-command-field">
        <span>{t('queueRouting.source')}</span>
        <select value={slotId} onChange={(event) => onChange(event.currentTarget.value)}>
          <option value="">{t('queueRouting.chooseSource')}</option>
          {sources.map((source) => (
            <option key={source.slot.slotId} value={source.slot.slotId}>
              {source.unitLabel} · {source.slotLabel} · {source.slot.detectedMaterial?.materialFamily ?? 'unknown'}
            </option>
          ))}
        </select>
      </label>

      {selectedSource && (
        <div className="queue-routing-source-status">
          <span className={`queue-routing-status ${compatibility === 'match' || compatibility === 'unconstrained' ? 'ready' : 'blocked'}`}>
            {compatibilityText(compatibility, t)}
          </span>
          <span className={`queue-routing-status ${route?.state === 'ready' ? 'ready' : 'blocked'}`}>
            {routeText(route, t)}
          </span>
        </div>
      )}
    </article>
  );
}

function RoutingAlert({ text }: { text: string }) {
  return <div className="queue-routing-alert" role="alert">{text}</div>;
}

export function QueueEntryActions({ entry }: { entry: QueueViewModel }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [dispatchKey, setDispatchKey] = useState<string | null>(null);
  const [acceptedKey] = useState(() => crypto.randomUUID());
  const [notAcceptedKey] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dispatch = async () => {
    const idempotencyKey = dispatchKey ?? crypto.randomUUID();
    setDispatchKey(idempotencyKey);
    setBusy(true);
    setError(null);
    try {
      await dispatchPrintJob(entry.queueId, idempotencyKey);
      setDispatchKey(null);
      await refreshQueue(queryClient);
    } catch (cause) {
      setError(errorMessage(cause));
      await refreshQueue(queryClient);
    } finally {
      setBusy(false);
    }
  };

  const reconcile = async (accepted: boolean) => {
    const prompt = accepted
      ? t('alpha.queueCommand.confirmAccepted')
      : t('alpha.queueCommand.confirmNotAccepted');
    if (!window.confirm(prompt)) return;
    setBusy(true);
    setError(null);
    try {
      await reconcilePrintJob(entry.queueId, accepted, accepted ? acceptedKey : notAcceptedKey);
      await refreshQueue(queryClient);
    } catch (cause) {
      setError(errorMessage(cause));
      await refreshQueue(queryClient);
    } finally {
      setBusy(false);
    }
  };

  const retryableFailure = entry.state === 'failed' && entry.retryable === true;
  if (!['pending', 'blocked', 'indeterminate'].includes(entry.state) && !retryableFailure && !error) return null;

  return (
    <div className="queue-entry-actions">
      {(entry.state === 'pending' || entry.state === 'blocked' || retryableFailure) && (
        <button className="text-button" type="button" disabled={busy} onClick={() => void dispatch()}>
          {busy
            ? t('alpha.queueCommand.sending')
            : retryableFailure
              ? t('alpha.queueCommand.retryPrint')
              : t('alpha.queueCommand.startPrint')}
        </button>
      )}
      {entry.state === 'indeterminate' && (
        <>
          <button className="text-button warning-text" type="button" disabled={busy} onClick={() => void reconcile(true)}>
            {t('alpha.queueCommand.confirmStarted')}
          </button>
          <button className="text-button" type="button" disabled={busy} onClick={() => void reconcile(false)}>
            {t('alpha.queueCommand.confirmNotStarted')}
          </button>
        </>
      )}
      {error && <small className="warning-text">{error}</small>}
    </div>
  );
}

async function refreshQueue(queryClient: ReturnType<typeof useQueryClient>): Promise<void> {
  await queryClient.invalidateQueries({ queryKey: ['queue', 'snapshot'] });
}

function stripKnownExtension(filename: string): string {
  return filename.replace(/\.(gcode|3mf)$/i, '');
}

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KiB`;
  return `${(size / 1024 / 1024).toFixed(1)} MiB`;
}

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : String(cause);
}

function isReconciliationError(cause: unknown): boolean {
  return cause instanceof CommandApiError
    && (cause.code === 'queue_reconciliation_required' || cause.code === 'reconciliation_required');
}

function dispatchPhase(result: QueueCommandResult): SubmitPhase {
  if (result.state === 'indeterminate' || result.reconciliationRequired) return 'indeterminate';
  if (result.state === 'blocked') return 'blocked';
  if (result.state === 'failed') return 'failed';
  return 'accepted';
}

function dispatchButtonLabel(phase: SubmitPhase, t: (key: string) => string): string {
  if (phase === 'error') return t('alpha.queueCommand.resendDispatchRequest');
  if (phase === 'blocked') return t('alpha.queueCommand.tryStartAgain');
  if (phase === 'failed') return t('alpha.queueCommand.retryPrint');
  return t('alpha.queueCommand.startPrint');
}

function phaseLabel(phase: SubmitPhase, t: (key: string) => string): string {
  if (phase === 'hashing') return t('alpha.queueCommand.hashing');
  if (phase === 'staging') return t('alpha.queueCommand.uploading');
  if (phase === 'inspecting') return t('queueRouting.inspecting');
  if (phase === 'reviewing') return t('queueRouting.reviewTitle');
  if (phase === 'enqueuing') return t('alpha.queueCommand.enqueuing');
  if (phase === 'queued') return t('alpha.queueCommand.queued');
  if (phase === 'dispatching') return t('alpha.queueCommand.dispatching');
  if (phase === 'blocked') return t('alpha.queueCommand.blocked');
  if (phase === 'accepted') return t('alpha.queueCommand.accepted');
  if (phase === 'indeterminate') return t('alpha.queueCommand.indeterminate');
  if (phase === 'failed') return t('alpha.queueCommand.failed');
  if (phase === 'error') return t('alpha.queueCommand.requestFailed');
  return t('alpha.queueCommand.ready');
}

function phaseText(phase: SubmitPhase, t: (key: string) => string): string {
  if (phase === 'queued') return t('alpha.queueCommand.queuedText');
  if (phase === 'blocked') return t('alpha.queueCommand.blockedText');
  if (phase === 'accepted') return t('alpha.queueCommand.acceptedText');
  if (phase === 'indeterminate') return t('alpha.queueCommand.indeterminateShort');
  if (phase === 'failed') return t('alpha.queueCommand.failedText');
  if (phase === 'error') return t('alpha.queueCommand.retrySameCommand');
  if (['hashing', 'staging', 'inspecting', 'enqueuing', 'dispatching'].includes(phase)) {
    return t('alpha.queueCommand.workingText');
  }
  return t('alpha.queueCommand.readyText');
}

function compatibilityText(
  compatibility: ReturnType<typeof materialCompatibility> | undefined,
  t: (key: string) => string,
): string {
  if (compatibility === 'match') return t('queueRouting.materialMatch');
  if (compatibility === 'mismatch') return t('queueRouting.materialMismatch');
  if (compatibility === 'unknown') return t('queueRouting.materialUnknown');
  return t('queueRouting.materialUnconstrained');
}

function routeText(
  route: ReturnType<typeof routePreview> | undefined,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  if (!route) return t('queueRouting.routeUnknown');
  if (route.state === 'ready') return t('queueRouting.routeReady', { toolheads: route.toolheadLabels.join(', ') });
  if (route.state === 'ambiguous') return t('queueRouting.routeAmbiguous');
  if (route.state === 'incompatible') return t('queueRouting.routeIncompatible');
  if (route.state === 'stale') return t('queueRouting.routeStale');
  return t('queueRouting.routeUnknown');
}
