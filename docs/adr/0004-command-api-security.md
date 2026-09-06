# ADR 0004: Command API security and idempotency

- **Status:** Accepted; browser/deployment trust details extended by ADR 0005
- **Date:** 2026-09-04
- **Implementation update:** 2026-09-06
- **Decision owners:** FoxForge maintainers

## Context

Remote mutations can start/stop physical equipment, alter durable queue state or change inventory/accounting. Authentication alone is insufficient: duplicate requests, timeouts and ambiguous printer outcomes require explicit idempotency/reconciliation semantics.

## Decision

### Explicit fail-closed authentication

Protected commands use a deployment-supplied Bearer credential (`FOXFORGE_COMMAND_TOKEN`). If no command credential is configured, protected commands are disabled rather than anonymously enabled.

Tokens are runtime secrets and do not belong in `config.json`, SQLite business DTOs, URLs or logs.

ADR 0005 defines the browser/deployment trust model and rejects tokenless trusted-browser bootstrap in production.

### FoxForge principals and permissions

Inbound authentication resolves to a FoxForge principal with explicit permissions. Current operator permissions include:

- `queue.write`;
- `printer.control`;
- `printer.config`;
- `inventory.write`.

`admin.config` remains distinct and is not granted merely because the alpha operator credential is valid.

Application/domain services do not receive raw Bearer tokens.

### Request correlation

Protected requests have a FoxForge request ID returned to the caller for diagnostics. Request IDs are not idempotency keys and must not contain secrets.

### Durable idempotency

Externally callable side-effecting commands use `Idempotency-Key` unless a route documents a stronger intrinsic identity.

The durable record binds authenticated principal/operation + canonical request fingerprint + command lifecycle/result. Same-key/same-request replay returns the same logical result. Same-key/changed-request conflicts.

A command whose side effect may have happened but whose result cannot be proven must not be blindly repeated merely because the HTTP client timed out.

Feature-level durable identities remain separate. For example, queue `dispatchId` and job-control `controlId` are not HTTP idempotency keys.

### Audit

Authenticated mutations write append-only secret-free audit evidence. Preflight audit failure blocks the command before side effects. Audit never stores Bearer credentials, printer access codes or raw idempotency keys.

### Normalized errors

HTTP responses use FoxForge-owned normalized error codes/retryability rather than leaking vendor exceptions/tracebacks. Retryability is part of the contract; clients must not infer it from generic 5xx status alone.

### Printer-side ambiguity

Queue print start and common job controls preserve `INDETERMINATE`/uncertain outcomes. Browser/API layers refresh/reconcile observation; they do not automatically resend the physical side effect.

## Current command families

Implemented protected command families include:

- printer configuration/discovery-related mutations;
- artifact/queue enqueue/dispatch/reconciliation;
- inventory mutations;
- common Pause/Resume/Cancel.

Printer configuration adds extra test-before-save/rollback safety documented in `docs/design/app-managed-printer-setup.md`.

## Security invariants

- no mutation is enabled by printer reachability alone;
- proxy forwarding headers are not FoxForge principals;
- credentials are never returned by read DTOs;
- idempotency record is durable across restart where required;
- same logical terminal failed setup replay does not re-run the connection attempt;
- ambiguous physical side effects remain non-retryable until observation/reconciliation resolves them.

## Acceptance criteria

- missing/invalid credential fails closed;
- explicit permissions gate command families;
- same-key unchanged replay is deterministic across restart;
- changed payload under same key conflicts;
- audit is append-only and secret-free;
- raw vendor/internal exceptions do not cross the public command boundary;
- clients cannot weaken queue/job-control/setup idempotency by automatic resend.
