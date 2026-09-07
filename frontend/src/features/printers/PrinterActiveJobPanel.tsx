// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useTranslation } from 'react-i18next';

import type { PrinterViewModel } from '../../domain';
import { formatDuration, formatPercent } from '../../viewModel';
import { JobControlActions } from './JobControlActions';

export function PrinterActiveJobPanel({
  printer,
  controls = false,
}: {
  printer: PrinterViewModel;
  controls?: boolean;
}) {
  const { t } = useTranslation();
  const job = printer.snapshot.activeJob;
  if (!job) return null;

  return (
    <section className={`panel printer-active-job ${controls ? 'printer-control-panel' : ''}`}>
      <div className="printer-section-heading">
        <div>
          <div className="eyebrow">{t('printerDetail.activeJob')}</div>
          <h3>{job.name ?? t('printerDetail.unnamedJob')}</h3>
        </div>
        <strong className="printer-job-percent">{formatPercent(job.progress)}</strong>
      </div>
      <Progress value={job.progress} />
      <div className="printer-job-facts">
        <Fact label={t('printerDetail.elapsed')} value={formatDuration(job.elapsedSeconds)} />
        <Fact label={t('printerDetail.remainingTime')} value={formatDuration(job.remainingSeconds)} />
        <Fact label={t('printerDetail.layer')} value={`${job.currentLayer ?? '—'} / ${job.totalLayers ?? '—'}`} />
        <Fact label={t('printerDetail.jobState')} value={t(`alpha.status.${job.state}`)} />
      </div>
      {controls && <JobControlActions printer={printer} />}
    </section>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function Progress({ value = 0 }: { value?: number }) {
  return (
    <div className="progress-track">
      <div className="progress-value" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} />
    </div>
  );
}
