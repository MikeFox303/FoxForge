# Queue command UI

- **Status:** implemented; evolved through Alpha 4 and current Pre-Alpha 5 source
- **Updated:** 2026-09-06
- **Backend contract:** [Queue command API and artifact staging](queue-command-api.md)

## Purpose

The browser is a thin orchestration layer over the durable queue contract. It must not introduce client filesystem paths, invent a second state machine or weaken idempotency/reconciliation safety.

## Browser print flow

For ordinary formats that do not require material routing:

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

For a 3MF-capable printer that advertises material bindings, Pre-Alpha 5 inserts a mandatory review gate:

```text
select 3MF
  -> WebCrypto SHA-256
  -> authenticated byte staging
  -> immutable print-plan inspection
  -> choose plate when required
  -> review every logical material requirement
  -> explicitly bind each materialIndex to one loaded slotId
  -> preview material-family + source/toolhead compatibility
  -> enqueue(queueId + dispatchId + artifactId + plateIndex + materialBindings)
  -> server routing compiler revalidates and owns toolheadId
  -> PENDING / BLOCKED
  -> explicit dispatch
```

The browser never sends an arbitrary client/server path and never supplies compiler-owned `toolheadId`.

## Material-routing review

The material review is capability-driven. Generic UI checks `foxforge.print_execution` metadata such as accepted formats, plate-selection support and material-binding support. It does not branch on Bambu/X2D model names.

The browser displays only material sources currently reported as loaded. A selection is considered ready only when:

- the immutable print plan and selected plate are routing-ready;
- material-system and topology snapshots are present and not stale;
- every required material index has an explicit source binding;
- a constrained material family is known and matches the selected source;
- the source has a proven compatible toolhead route;
- an expected 3MF toolhead, when present, is reachable through that source.

Color is not an automatic chooser and is not used to infer a route. The browser preview is advisory defense-in-depth only; the server routing compiler performs the authoritative validation again before adapter assessment, and the Bambu adapter revalidates native source/topology state again before transport submission.

Changing the selected plate or any material binding creates a new logical enqueue identity and clears any prior queue result. The browser never silently reuses a previously reviewed route after operator intent changes.

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
- Bambu setup/reconnect diagnostics;
- immutable 3MF inspection and explicit material-binding review.

Automatic filament accounting remains frozen P3 work.

## Acceptance criteria

- file staging sends bytes + filename/hash only;
- 3MF material-binding capable printers require immutable inspection before enqueue;
- multi-plate jobs require explicit plate selection when the backend capability requires it;
- every routed material has an explicit operator-selected `slotId`;
- browser requests never include `toolheadId`;
- incompatible/unknown/stale material routes keep enqueue disabled;
- routing review remains usable without horizontal overflow on the phone acceptance viewport;
- queue/dispatch/HTTP identities are never conflated;
- only canonical retryable receipt-free failures expose retry;
- `INDETERMINATE` remains reconciliation-only;
- Operator Access credential stays memory-only;
- realtime updates refresh canonical HTTP queue state;
- frontend EN/RU/UK/typecheck/unit/build/browser gates remain green.
