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

export class CommandAuthenticationRequiredError extends Error {
  constructor() {
    super('FoxForge write controls are locked. Enter the operator command token to enable commands for this tab.');
    this.name = 'CommandAuthenticationRequiredError';
  }
}

let operatorToken: string | null = null;

export function setOperatorCommandToken(token: string): void {
  const normalized = token.trim();
  if (!normalized) throw new Error('Operator command token must not be empty.');
  operatorToken = normalized;
}

export function clearOperatorCommandToken(): void {
  operatorToken = null;
}

export function hasOperatorCommandToken(): boolean {
  return operatorToken !== null;
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
  if (!operatorToken) throw new CommandAuthenticationRequiredError();

  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${operatorToken}`);
  if (options.json) headers.set('Content-Type', 'application/json');
  if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey);

  const response = await fetch(path, {
    method: options.method ?? 'GET',
    headers,
    body: options.json ? JSON.stringify(options.json) : options.body,
  });
  if (response.status === 401) operatorToken = null;
  return response;
}

export function clearOperatorSessionForTests(): void {
  clearOperatorCommandToken();
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
