# Command security implementation foundation

Status: implementation design for ADR 0004.

Related: `docs/adr/0004-command-api-security.md`, `docs/design/public-api-v1.md`, queue idempotency design, inventory foundation.

## Scope

This phase implements reusable command-security infrastructure **without exposing any HTTP mutation route**.

Implemented boundaries:

- `foxforge.api.security` owns inbound Bearer authentication, FoxForge principals/permissions, request-ID normalization and safe command error envelopes;
- `foxforge.application.commands` owns command idempotency/audit models, ports and services independent of HTTP/vendor transports;
- `foxforge.infrastructure.commands.SQLiteCommandStore` owns restart-safe SQLite persistence for idempotency claims/results and structured audit records.

The existing read API remains unchanged.

## Authentication

`BearerCommandAuthenticator` accepts a deployment-supplied token value and fails closed when no token is supplied. The future runtime composition will pass `FOXFORGE_COMMAND_TOKEN`; this foundation deliberately does not add a route that consumes it yet.

A successful static token resolves to principal `static-operator` with:

- `queue.write`;
- `printer.control`;
- `inventory.write`.

It does not grant `admin.config`.

Credential comparison uses `hmac.compare_digest`. The authenticator representation never includes the configured token.

## Request correlation and errors

Valid UUID `X-Request-Id` values may be retained by future command handlers; otherwise a new UUID is generated.

Command security failures use the ADR 0004 normalized error envelope and `X-Request-Id`. Unauthorized responses also emit `WWW-Authenticate: Bearer`.

## Durable idempotency

The HTTP idempotency key remains opaque to command implementations.

`CommandIdempotencyService`:

1. validates an 8-128 character bounded key;
2. hashes the key with SHA-256 before persistence;
3. canonicalizes the command payload as sorted compact JSON and hashes that as the request fingerprint;
4. scopes claims by principal + operation + key hash;
5. returns `created=True` only for the first durable claim;
6. replays the same stored record for same key/same fingerprint;
7. raises `CommandIdempotencyConflictError` for same key/changed fingerprint;
8. persists normalized completed or indeterminate results for restart-safe replay.

An `IN_PROGRESS` record intentionally survives process restart. Future command handlers must not start the side effect again merely because the client retried after a disconnect.

This layer complements rather than replaces QueueService `dispatch_id` and `INDETERMINATE` semantics.

## Audit

`CommandAuditService` persists structured records containing request ID, principal, action, target, outcome, timestamp, normalized error code and a SHA-256 digest of the idempotency key when present.

Raw bearer tokens and raw idempotency keys are not audit fields.

## SQLite schema

`SQLiteCommandStore` uses the same application database path as the queue/inventory stores when composed into the runtime later.

Tables:

- `command_idempotency`, primary key `(principal_id, operation, key_hash)`;
- `command_audit`, primary key `audit_id` plus created-at index.

Connections use a five-second timeout/busy timeout and WAL-compatible initialization, consistent with the current single-container FoxForge deployment boundary.

## Deliberately deferred

This phase does not add:

- inventory/queue/printer HTTP mutations;
- browser token storage or a cookie/session login;
- printer credential/configuration writes;
- trusted forwarded-header authentication;
- raw vendor errors or vendor DTOs in command responses.

The next implementation slice should expose narrow inventory mutations first because InventoryService already has exact Decimal accounting and intrinsic per-adjustment idempotency. The HTTP command identity should be propagated into that ledger rather than creating a second accounting identity.

## Acceptance criteria

- no command route exists yet;
- read API behavior remains backward compatible;
- unset command credential fails closed at the authenticator boundary;
- token comparison is constant-time and tokens are not represented/logged by the security primitive;
- static operator permissions exclude `admin.config`;
- request IDs and normalized security error envelopes are tested;
- same idempotency key/same fingerprint replays without a second claim;
- same key/changed fingerprint conflicts;
- principal and operation are part of idempotency scope;
- completed and indeterminate results persist across a new SQLite store instance;
- in-progress claims survive restart rather than disappearing;
- audit records survive restart and contain only a key digest, not the raw key;
- command application/persistence code has no printer/vendor imports;
- Ruff, format and full pytest matrix pass on Python 3.12 and 3.13.
