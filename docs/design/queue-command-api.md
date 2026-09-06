# Queue command API and artifact staging

- **Status:** implemented alpha contract
- **Updated:** 2026-09-06
- **Related:** ADR 0001, ADR 0004, [queue dispatch](queue-dispatch.md), [queue retry policy](queue-retry-policy.md), [artifact lifecycle](artifact-lifecycle.md)

## Purpose

The public queue workflow must never accept an arbitrary server filesystem path and must not bypass the durable queue/`PrintExecutionCapability` safety boundary.

## Artifact staging

Clients upload bytes to the authenticated artifact endpoint with a declared filename and SHA-256. FoxForge streams the body into server-owned temporary storage, enforces the configured size/capacity policy, computes SHA-256 and atomically publishes content only after verification.

Artifact identity is content-addressed by verified SHA-256. Public DTOs expose safe metadata only; `/data/artifacts/...` filesystem paths remain private.

Supported initial print formats are `.gcode` and `.3mf` according to printer capability.

Artifact quota, free-space reserve, retention and safe orphan/temp cleanup are implemented under [artifact-lifecycle.md](artifact-lifecycle.md). Queue-referenced artifacts are not garbage-collection candidates.

## Enqueue and dispatch identities

Queue creation resolves only a server-owned `artifactId` and constructs the common `PrintExecutionRequest`.

Three identities remain deliberately distinct:

- queue resource identity;
- durable printer-side `dispatchId`;
- per-HTTP-command `Idempotency-Key`.

The browser must not collapse them into one value.

## Dispatch safety

Dispatch always calls `QueueService.dispatch()` and the typed `PrintExecutionCapability`.

Binding invariants:

- `DISPATCHING` persists before printer submission;
- confirmed receipts are never blindly resubmitted;
- ambiguous printer start becomes durable `INDETERMINATE`;
- `INDETERMINATE` is reconciliation-only;
- a later retry is permitted only for an explicitly retryable, receipt-free pre-start failure;
- same logical HTTP replay cannot send the side effect again.

## Reconciliation

Explicit reconciliation may resolve `DISPATCHING`/`INDETERMINATE` as accepted or not accepted according to the durable queue contract. HTTP idempotency replay is evaluated before current queue-state drift so a previously completed command remains the same logical command result.

## Command authentication and audit

Artifact/queue mutations use the normal command-security layer:

- Bearer authentication and permissions;
- request correlation;
- durable idempotency where required;
- normalized errors;
- preflight and terminal append-only audit.

Audit stores a digest of the HTTP idempotency key, never the raw key. Bearer credentials and printer access codes are not audit fields.

## Browser workflow

The shipped browser flow is:

1. select a local file;
2. hash it in the browser;
3. upload bytes + expected digest, never a client/server path;
4. enqueue the verified artifact;
5. start/dispatch as a separate protected command;
6. refresh canonical queue state after realtime/command changes;
7. reconcile uncertainty rather than blindly retrying `INDETERMINATE`.

## Current scope

Implemented:

- browser-safe upload/staging;
- durable enqueue/dispatch/reconciliation;
- content-addressed artifacts;
- capacity/retention/GC policy;
- common Pause/Resume/Cancel through the separate job-control contract;
- production browser acceptance for representative queue flow.

Still separate/future:

- resumable/chunked upload protocols;
- distributed multi-worker command leases/CAS;
- deep Bambu print options beyond typed capability contracts;
- complete physical X2D/OpenKE acceptance.

## Acceptance criteria

- public APIs never accept arbitrary server file paths;
- uploaded bytes are bounded and SHA-256 verified;
- duplicate content does not create duplicate payloads;
- queue commands preserve durable idempotency/dispatch identities;
- no handler bypasses `QueueService`/typed execution capability;
- ambiguous start never causes automatic duplicate dispatch;
- audit remains secret-free;
- artifact GC cannot remove queue-referenced content;
- physical printer validation is claimed only from physical evidence.
