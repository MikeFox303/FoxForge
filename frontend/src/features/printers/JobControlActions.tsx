// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { CommandApiError } from '../../data/commandClient';
import type { JobControlAction, PrinterViewModel } from '../../domain';
import { controlPrinterJob, createJobControlIdentity } from './jobControlClient';

type ControlPhase = 'idle' | 'sending' | 'uncertain';

export function JobControlActions({ printer }: { printer: PrinterViewModel }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [phase, setPhase] = useState<ControlPhase>('idle');
  const [activeAction, setActiveAction] = useState<JobControlAction | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const jobControl = printer.capabilities.find((item) => item.capabilityId === 'foxforge.job_control' && item.majorVersion === 1);
  const job = printer.snapshot.activeJob;

  useEffect(() => {
    setPhase('idle');
    setActiveAction(null);
    setMessage(null);
  }, [printer.snapshot.observedAt, job?.vendorJobId, job?.state]);

  const actions = useMemo(() => {
    if (!jobControl || !job?.vendorJobId || printer.snapshot.stale || printer.snapshot.connection !== 'connected') return [];
    const supported = new Set(jobControl.supportedActions ?? []);
    const result: JobControlAction[] = [];
    if (job.state === 'printing' && supported.has('pause')) result.push('pause');
    if (job.state === 'paused' && supported.has('resume')) result.push('resume');
    if (['preparing', 'printing', 'paused'].includes(job.state) && supported.has('cancel')) result.push('cancel');
    return result;
  }, [jobControl, job, printer.snapshot.connection, printer.snapshot.stale]);

  if (!jobControl || !job) return null;
  if (!job.vendorJobId) {
    return <div className="printer-control-warning">{t('jobControl.identityRequired')}</div>;
  }

  const execute = async (action: JobControlAction) => {
    if (phase !== 'idle') return;
    if (action === 'cancel' && !window.confirm(t('jobControl.confirmCancel'))) return;

    setPhase('sending');
    setActiveAction(action);
    setMessage(null);
    const identity = createJobControlIdentity();
    try {
      await controlPrinterJob({
        identity,
        printerId: printer.identity.printerId,
        vendorJobId: job.vendorJobId!,
        action,
      });
      setMessage(t(`jobControl.accepted.${action}`));
      setPhase('idle');
      await queryClient.invalidateQueries({ queryKey: ['fleet', 'snapshot'] });
    } catch (error) {
      const commandError = error instanceof CommandApiError ? error : null;
      const uncertain = !commandError || commandError.code === 'job_control_indeterminate' || commandError.code === 'job_control_reconciliation_required';
      if (uncertain) {
        setPhase('uncertain');
        setMessage(t('jobControl.uncertain'));
      } else {
        setPhase('idle');
        setMessage(commandError.message);
      }
      await queryClient.invalidateQueries({ queryKey: ['fleet', 'snapshot'] });
    } finally {
      setActiveAction(null);
    }
  };

  if (actions.length === 0) return null;

  return (
    <div className="stack-sm">
      <div className="printer-control-row" aria-label={t('jobControl.controls')}>
        {actions.map((action) => (
          <button
            type="button"
            key={action}
            className={`secondary-button ${action === 'cancel' ? 'danger-button' : ''}`}
            disabled={phase !== 'idle'}
            onClick={() => void execute(action)}
          >
            {phase === 'sending' && activeAction === action ? t('jobControl.sending') : t(`jobControl.actions.${action}`)}
          </button>
        ))}
      </div>
      {message && (
        <div className={`printer-control-message ${phase === 'uncertain' ? 'warning' : ''}`} role={phase === 'uncertain' ? 'alert' : 'status'}>
          {message}
        </div>
      )}
    </div>
  );
}
