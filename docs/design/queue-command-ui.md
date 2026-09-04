# Queue command UI

**Status:** implemented in post-`v0.1.0-alpha.2` development source  
**Applies to:** React browser client over ADR 0004 authenticated command APIs  
**Backend contract:** [Queue command API and artifact staging](queue-command-api.md)

## Context

FoxForge already owns a durable queue and a safe command API for staging print artifacts, enqueueing jobs, dispatching a print and reconciling uncertain starts. The browser must not weaken those guarantees by introducing client filesystem paths, inventing a second queue state machine or treating every failed/blocked command as a generic retryable action.

The UI therefore acts as a thin orchestration layer above the FoxForge API and preserves the queue's existing durable identities and safety states.

## Browser print flow

```text
File selected in browser
        |
        v
WebCrypto SHA-256
        |
        v
POST /api/v1/artifacts
(bytes + filename + expected hash)
        |
        v
content-addressed staged artifact
        |
        v
POST /api/v1/queue
(queueId + dispatchId + artifactId)
        |
        v
PENDING durable queue entry
        |
        v
explicit POST .../dispatch
        |
        +--> BLOCKED
        +--> FAILED (retry only when retryable=true and no receipt)
        +--> ACCEPTED / lifecycle states
        +--> INDETERMINATE --> explicit reconciliation only
```

The browser never sends an arbitrary local/server path. The selected `File` object is used only for hashing and request bytes; the backend reconstructs its own `LocalPrintArtifact` from trusted staged storage.

## Identity model

Three identities have different responsibilities and must not be conflated.

### `queueId`

Created by the browser before enqueue. It identifies the durable FoxForge queue resource and is reused when an enqueue HTTP request must be replayed.

### `dispatchId`

Created with the logical queue job and persisted inside the queue request. It is the printer-submission idempotency identity owned by `QueueService` and remains stable for the lifetime of that queue entry, including safe pre-start retries.

### HTTP `Idempotency-Key`

Identifies one externally callable command attempt under ADR 0004.

For dispatch:

- create a key before sending the HTTP request;
- if the request outcome is unknown because the browser/network failed before receiving a conclusive response, replay the **same key**;
- after a conclusive `BLOCKED` response, a later intentional reassessment/start uses a **new HTTP key** while keeping the queue's original `dispatchId`;
- after a conclusive receipt-free `FAILED` response, a new HTTP key may be used only when the backend exposes `error.retryable=true`;
- receipt-bearing failures never expose a dispatch retry;
- `DISPATCHING` and `INDETERMINATE` never receive a new dispatch attempt.

This prevents both duplicate side effects and the opposite failure mode where a completed `BLOCKED` command is replayed forever under one old HTTP key even after printer conditions change.

## UI state model

The create/dispatch panel exposes explicit phases:

- `idle`
- `hashing`
- `staging`
- `enqueuing`
- `queued`
- `dispatching`
- `blocked`
- `accepted`
- `failed`
- `indeterminate`
- request `error`

`BLOCKED`, `FAILED` and `INDETERMINATE` are not interchangeable:

- **BLOCKED** means assessment completed without a printer start; the operator may intentionally reassess later.
- **FAILED** exposes retry only when the canonical API read model marks the pre-start error retryable.
- **INDETERMINATE** means FoxForge cannot prove whether the side effect happened and therefore offers only reconciliation actions.

The UI never converts an uncertain print start into a generic "Retry" button.

## Reconciliation

For an `INDETERMINATE` queue entry the operator must verify the physical/live printer state and explicitly choose one of:

- confirm that printing started;
- confirm that printing did not start.

Both reconciliation commands are authenticated and idempotent. The UI asks for explicit confirmation because reconciliation changes the durable interpretation of an uncertain printer-side effect.

## Shared browser command client

Printer setup and queue commands use one browser command client for:

- `POST /api/v1/operator-session` bootstrap;
- bearer-token attachment;
- `Idempotency-Key` headers;
- normalized command errors;
- clearing a cached browser token after HTTP 401.

Feature clients remain typed and domain-specific; the common client does not learn printer, inventory or queue business semantics.

## Current limitations

This slice intentionally does not add:

- plate selection or material-binding controls;
- streaming/incremental SHA-256 computation or byte-progress upload UI;
- pause/resume/cancel controls;
- automatic print dispatch when a job is enqueued;
- realtime WebSocket/SSE updates;
- persisted browser draft recovery across a full page reload.

`crypto.subtle.digest()` currently hashes the whole selected file in browser memory. The backend's upload bound remains authoritative. A future streaming hash/progress implementation may improve very-large-file UX without changing the API trust boundary.

## Acceptance criteria

- a browser-selected `.gcode`/`.3mf` reaches staging as bytes plus filename/hash, never a client filesystem path;
- queue creation uses a stable browser-created `queueId`, `dispatchId` and enqueue idempotency key;
- an uncertain dispatch request can be replayed with the same HTTP key;
- a completed `BLOCKED` attempt does not pin all later intentional attempts to the old HTTP key;
- only backend-confirmed retryable receipt-free `FAILED` entries expose retry;
- `INDETERMINATE` exposes reconciliation only;
- printer setup and queue writes share authentication/session plumbing without sharing feature semantics;
- EN/RU/UK translation keys remain aligned;
- frontend typecheck, unit tests, production build and unified-container smoke remain green.

## Follow-up

1. Run physical Bambu X2D and Moonraker/OpenKE upload/start/reconciliation validation.
2. Add typed common pause/resume/cancel capability and command APIs before exposing those controls in the UI.
3. Add realtime application-event delivery and query-cache updates.
4. Add trustworthy material binding and queue-driven filament accounting.
5. Consider streaming hashing/upload progress for very large artifacts without weakening backend verification.
