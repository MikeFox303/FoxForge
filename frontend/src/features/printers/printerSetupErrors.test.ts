// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it } from 'vitest';

import { CommandApiError } from '../../data/commandClient';
import { setupCommandErrorMessage, setupOutcomeErrorMessage } from './printerSetupErrors';

describe('printer setup errors', () => {
  it('localizes stable Add Printer connection codes', () => {
    const error = new CommandApiError('server fallback', {
      status: 422,
      code: 'printer_connection_authentication_failed',
    });

    expect(setupCommandErrorMessage(error, 'ru')).toContain('LAN access code');
    expect(setupCommandErrorMessage(error, 'uk')).toContain('код доступу');
    expect(setupCommandErrorMessage(error, 'en')).toContain('rejected');
  });

  it('gives the initial-state stage priority over generic timeout copy', () => {
    const message = setupOutcomeErrorMessage(
      {
        code: 'timeout',
        message: 'server fallback',
        retryable: true,
        vendorCode: 'initial_state_timeout',
      },
      'ru',
    );

    expect(message).toContain('серийный номер');
    expect(message).not.toContain('TCP-порта 8883');
  });

  it('falls back to the sanitized server message for unknown normalized errors', () => {
    expect(setupOutcomeErrorMessage(
      {
        code: 'remote_rejected',
        message: 'Printer connection validation failed.',
        retryable: false,
      },
      'en',
    )).toBe('Printer connection validation failed.');
  });

  it('does not override unrelated command errors', () => {
    const error = new CommandApiError('printer exists', { status: 409, code: 'printer_exists' });
    expect(setupCommandErrorMessage(error, 'ru')).toBeNull();
  });
});
