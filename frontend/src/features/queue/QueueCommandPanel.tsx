// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { CommandApiError } from '../../data/commandClient';
import type { FleetData, QueueViewModel } from '../../domain';
import '../../queue-command.css';
import {
  createQueueJobIdentity,
  dispatchPrintJob,
  enqueuePrintJob,
  reconcilePrintJob,
  sha256File,
  stagePrintArtifact,
  type QueueCommandResult,
  type QueueJobIdentity,
  type StagedArtifact,
} from './queueCommandClient';

type SubmitPhase =
  | 'idle'
  | 'hashing'
  | 'staging'
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
  queue?: QueueCommandResult;
  dispatchIdempotencyKey?: string;
}

export function QueueCommandPanel({ fleet }: { fleet: FleetData }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const printers = useMemo(
    () => fleet.printers.filter((printer) => (
      printer.capabilities.some((item) => item.capabilityId === 'foxforge.print_execution')
    )),
    [fleet.printers],
  );
  const [file, setFile] = useState<File | null>(null);
  const [printerId, setPrinterId] = useState('');
  const [requestedName, setRequestedName] = useState('');
  const [pending, setPending] = useState<PendingJob | null>(null);
  const [phase, setPhase] = useState<SubmitPhase>('idle');
  const [error, setError] = useState<string | null>(null);

  const busy = ['hashing', 'staging', 'enqueuing', 'dispatching'].includes(phase);
  const canEnqueue = file !== null && printerId !== '' && !busy && !pending?.queue;
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
    resetLogicalJob();
  };

  const onPrinterChange = (value: string) => {
    setPrinterId(value);
    resetLogicalJob();
  };

  const addToQueue = async () => {
    if (!file || !printerId) return;
    setError(null);
    const logicalJob = pending ?? {
      identity: createQueueJobIdentity(),
      file,
      printerId,
      requestedName: requestedName.trim(),
    };
    setPending(logicalJob);

    try {
      setPhase('hashing');
      const sha256 = logicalJob.sha256 ?? await sha256File(logicalJob.file);
      const withHash = { ...logicalJob, sha256 };
      setPending(withHash);

      setPhase('staging');
      const artifact = logicalJob.artifact ?? await stagePrintArtifact(logicalJob.file, sha256);
      const withArtifact = { ...withHash, artifact };
      setPending(withArtifact);

      setPhase('enqueuing');
      const queue = await enqueuePrintJob({
        identity: logicalJob.identity,
        printerId: logicalJob.printerId,
        artifactId: artifact.artifactId,
        requestedName: logicalJob.requestedName,
      });
      setPending({ ...withArtifact, queue });
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
              <option key={printer.identity.printerId} value={printer.identity.printerId}>
                {printer.identity.displayName}
              </option>
            ))}
          </select>
          <small>{printers.length ? t('alpha.queueCommand.printerHint') : t('alpha.queueCommand.noCapablePrinter')}</small>
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

      <div className="queue-command-status" role="status" aria-live="polite">
        <strong>{phaseLabel(phase, t)}</strong>
        <span>{phaseText(phase, t)}</span>
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
          <button className="primary-button" type="button" disabled={!canEnqueue} onClick={() => void addToQueue()}>
            {phase === 'error' ? t('alpha.queueCommand.retryAddRequest') : t('alpha.queueCommand.addToQueue')}
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
  if (['hashing', 'staging', 'enqueuing', 'dispatching'].includes(phase)) return t('alpha.queueCommand.workingText');
  return t('alpha.queueCommand.readyText');
}
