// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useTranslation } from 'react-i18next';

import type { PrinterViewModel } from '../../domain';
import { printerTone } from '../../viewModel';
import { printerStatusTranslationKey } from './printerPresentation';

export function PrinterStatusBadge({ printer }: { printer: PrinterViewModel }) {
  const { t } = useTranslation();
  const tone = printerTone(printer);
  const label = t(`alpha.status.${printerStatusTranslationKey(printer)}`);

  return (
    <span className={`status-badge tone-${tone}`} aria-label={label}>
      <span className={`status-dot ${tone}`} aria-hidden="true" />
      {label}
    </span>
  );
}
