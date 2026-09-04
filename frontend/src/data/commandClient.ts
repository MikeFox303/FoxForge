// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

export class CommandApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly retryable: boolean;

  constructor(message: string, options: { status: number; code?: string; retryable?: boolean }) {
    super(message);
    this.name = 'CommandApiError';
    this.status = options.status;
    this.code = options.code;
    this.retryable = options.retryable ?? false;
  }
}

let browserToken: string | null = null;
let sessionPromise: Promise<string> | null = null;

export async function ensureOperatorSession(): Promise<string> {
  if (browserToken) return browserToken;
  if (sessionPromise) return sessionPromise;

  sessionPromise = (async () => {
    const response = await fetch('/api/v1/operator-session', { method: 'POST' });
    const payload = await response.json().catch(() => null) as unknown;
    if (!response.ok) throw commandApiError(response.status, payload);
    if (!isRecord(payload) || typeof payload.accessToken !== 'string') {
      throw new Error('FoxForge returned an invalid operator-session response.');
    }
    browserToken = payload.accessToken;
    return browserToken;
  })();

  try {
    return await sessionPromise;
  } finally {
    sessionPromise = null;
  }
}

export async function authenticatedCommandJson<T>(
  path: string,
  options: {
    method?: string;
    json?: object;
    idempotencyKey?: string;
    headers?: HeadersInit;
    body?: BodyInit;
  } = {},
): Promise<T> {
  const response = await authenticatedCommandFetch(path, options);
  const payload = await response.json().catch(() => null) as unknown;
  if (!response.ok) throw commandApiError(response.status, payload);
  return payload as T;
}

export async function authenticatedCommandFetch(
  path: string,
  options: {
    method?: string;
    json?: object;
    idempotencyKey?: string;
    headers?: HeadersInit;
    body?: BodyInit;
  } = {},
): Promise<Response> {
  const token = await ensureOperatorSession();
  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  if (options.json) headers.set('Content-Type', 'application/json');
  if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey);

  const response = await fetch(path, {
    method: options.method ?? 'GET',
    headers,
    body: options.json ? JSON.stringify(options.json) : options.body,
  });
  if (response.status === 401) browserToken = null;
  return response;
}

export function clearOperatorSessionForTests(): void {
  browserToken = null;
  sessionPromise = null;
}

function commandApiError(status: number, payload: unknown): CommandApiError {
  if (isRecord(payload) && isRecord(payload.error)) {
    const message = typeof payload.error.message === 'string'
      ? payload.error.message
      : `FoxForge API request failed (${status}).`;
    return new CommandApiError(message, {
      status,
      code: typeof payload.error.code === 'string' ? payload.error.code : undefined,
      retryable: payload.error.retryable === true,
    });
  }
  return new CommandApiError(`FoxForge API request failed (${status}).`, { status });
}

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === 'object' && value !== null;
}
