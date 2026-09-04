// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { JobControlAction } from '../../domain';
import { authenticatedCommandJson } from '../../data/commandClient';

export interface JobControlIdentity {
  controlId: string;
  idempotencyKey: string;
}

export interface JobControlResult {
  controlId: string;
  printerId: string;
  action: JobControlAction;
  vendorJobId: string;
  accepted: boolean;
  replayed: boolean;
}

export function createJobControlIdentity(): JobControlIdentity {
  return {
    controlId: crypto.randomUUID(),
    idempotencyKey: crypto.randomUUID(),
  };
}

export async function controlPrinterJob(options: {
  identity: JobControlIdentity;
  printerId: string;
  vendorJobId: string;
  action: JobControlAction;
}): Promise<JobControlResult> {
  return authenticatedCommandJson<JobControlResult>(
    `/api/v1/printers/${encodeURIComponent(options.printerId)}/job-control`,
    {
      method: 'POST',
      idempotencyKey: options.identity.idempotencyKey,
      json: {
        controlId: options.identity.controlId,
        action: options.action,
        expectedVendorJobId: options.vendorJobId,
      },
    },
  );
}
