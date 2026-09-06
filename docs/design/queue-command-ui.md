# Queue command UI

- **Status:** implemented; evolved through Alpha 4 and current Pre-Alpha 5 source
- **Updated:** 2026-09-06
- **Backend contract:** [Queue command API and artifact staging](queue-command-api.md)

## Purpose

The browser is a thin orchestration layer over the durable queue contract. It must not introduce client filesystem paths, invent a second state machine or weaken idempotency/reconciliation safety.

## Browser print flow

```text
select File
  -> WebCrypto SHA-256
  -> authenticated byte staging
  -> content-addressed artifact
  -> enqueue(queueId + dispatchId + artifactId)
  -> PENDING
  -> explicit dispatch
       +-> BLOCKED
       +-> retryable receipt-free FAILED
       +-> ACCEPTED / lifecycle
       `-> INDETERMINATE -> reconciliation only
```

The browser never sends an arbitrary client/server path.

## Identity model

Three identities remain distinct:

- `queueId` — durable FoxForge queue resource;
- `dispatchId` — printer-side logical submission identity retained for the queue entry;
- HTTP `Idempotency-Key` — one externally callable command identity.

An uncertain HTTP request replays the same HTTP key. A later intentional attempt after a conclusive safe pre-start result uses a new HTTP key while retaining the queue's original `dispatchId`.

## State presentation

`BLOCKED`, `FAILED` and `INDETERMINATE` are not interchangeable.

- **BLOCKED:** side-effect-free eligibility failed; later reassessment may be intentional.
- **FAILED:** dispatch retry is shown only when canonical state marks a receipt-free pre-start error retryable.
- **INDETERMINATE:** no generic retry; explicit reconciliation/observation required.

## Reconciliation

When start acceptance is uncertain, the operator verifies physical/live state and explicitly records accepted/not-accepted according to the backend reconciliation contract. The UI never turns uncertainty into a blind Retry button.

## Authentication

Queue commands use the shared explicit Operator Access credential. Production does not depend on anonymous `/api/v1/operator-session` bootstrap.

The shared command client owns only:

- in-memory Bearer credential attachment;
- HTTP idempotency header handling;
- normalized command errors;
- clearing the credential after authentication failure/Lock.

Feature business semantics remain in typed queue/printer/inventory clients.

## Features added after Alpha 3

The original queue UI has since been joined by:

- common capability-driven Pause/Resume/Cancel;
- SSE query invalidation/replay-resync handling;
- production-browser acceptance;
- artifact lifecycle/capacity safeguards;
- current Bambu setup/reconnect diagnostics work.

Plate/material binding UX may evolve as trusted cross-vendor contracts are expanded. Automatic filament accounting remains frozen P3 work.

## Acceptance criteria

- file staging sends bytes + filename/hash only;
- queue/dispatch/HTTP identities are never conflated;
- only canonical retryable receipt-free failures expose retry;
- `INDETERMINATE` remains reconciliation-only;
- Operator Access credential stays memory-only;
- realtime updates refresh canonical HTTP queue state;
- frontend EN/RU/UK/typecheck/unit/build/browser gates remain green.
