// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { demoModeEnabled } from '../../data/apiClient';
import { PrinterSetupDialog } from './PrinterSetupDialog';

export function PrinterSetupLauncher() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const demo = demoModeEnabled();

  const changed = () => {
    void queryClient.invalidateQueries({ queryKey: ['fleet'] });
  };

  useEffect(() => {
    if (!open) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (demo) return null;

  return (
    <>
      <button
        className="secondary-button printer-setup-launcher"
        type="button"
        onClick={() => setOpen(true)}
      >
        {t('alpha.shell.addPrinter')}
      </button>
      {open && createPortal(
        <PrinterSetupDialog open onClose={() => setOpen(false)} onChanged={changed} />,
        document.body,
      )}
    </>
  );
}
