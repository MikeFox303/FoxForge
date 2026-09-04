# Queue command API and artifact staging

Status: implementation specification for PR #50

Related: ADR 0001, ADR 0004, `printer-contracts.md`, `queue-dispatch.md`, `queue-event-lifecycle.md`, `queue-retry-policy.md`, `public-api-v1.md`

## Context

FoxForge already has a durable queue state machine and vendor-independent `PrintExecutionCapability`, but `QueueService.enqueue()` consumes a `LocalPrintArtifact` whose `path` is an absolute server-side filesystem path. ADR 0004 explicitly forbids exposing that path as a public command parameter and requires authenticated, validated, restart-safe idempotent commands with structured audit evidence.

The HTTP queue phase therefore needs two boundaries at the same time:

1. a safe server-owned artifact staging layer that turns uploaded bytes into `LocalPrintArtifact` objects; and
2. authenticated queue commands that compose with the existing `dispatch_id`, `DISPATCHING` and `INDETERMINATE` invariants instead of bypassing them.

This phase remains single-process/single-container. It does not claim distributed queue locking or physical X2D/OpenKE validation.

## Decision

### 1. Clients upload bytes, never server paths

The upload endpoint is:

```text
POST /api/v1/artifacts
Authorization: Bearer <command credential>
Content-Type: application/octet-stream
X-FoxForge-Filename: <percent-encoded UTF-8 base filename>
X-FoxForge-Sha256: <64 hex characters>
```

The filename must be a base filename, not a path. `.gcode` and `.3mf` are the first accepted formats.

The body is streamed into a server-owned temporary directory. FoxForge calculates SHA-256 while writing, enforces a maximum byte limit even when `Content-Length` is absent, verifies the supplied digest and only then publishes the artifact atomically.

Default upload limit: **512 MiB**.

A hash mismatch or oversize body is rejected before the artifact can be enqueued.

### 2. Artifact identity is content-addressed

The artifact ID is the verified lowercase SHA-256 digest.

Persistent layout:

```text
/data/artifacts/
  .tmp/
  <sha256>/
    payload
    metadata.json
```

`metadata.json` contains only safe FoxForge metadata: schema version, artifact ID, filename, format, byte size and SHA-256. Queue/API responses never expose the internal `payload` path.

Uploading the same content hash and format again is an intrinsic idempotent replay and returns the existing artifact instead of storing a second copy. This stronger content identity is why the raw upload route does not require an additional `Idempotency-Key`.

### 3. Enqueue uses artifact IDs and explicit durable identities

The queue creation endpoint is:

```text
POST /api/v1/queue
Authorization: Bearer <command credential>
Idempotency-Key: <opaque key>
Content-Type: application/json
```

Request shape:

```json
{
  "queueId": "uuid",
  "dispatchId": "uuid",
  "printerId": "printer-id",
  "artifactId": "sha256",
  "selection": { "plateIndex": 0 },
  "materialBindings": [
    { "materialIndex": 0, "slotId": "opaque-slot-id" }
  ],
  "requestedName": "optional display name"
}
```

`selection`, `materialBindings` and `requestedName` are optional. Unknown fields are rejected.

The API resolves `artifactId` through the server-owned artifact store and constructs the existing common `PrintExecutionRequest`. A client cannot construct or override `LocalPrintArtifact.path`.

`queueId` and `dispatchId` are explicit UUIDs so retry/recovery refers to the same logical queue resource and printer side-effect identity.

### 4. Dispatch reuses QueueService safety boundaries

The dispatch endpoint is:

```text
POST /api/v1/queue/{queueId}/dispatch
Authorization: Bearer <command credential>
Idempotency-Key: <opaque key>
```

It calls `QueueService.dispatch()` rather than a vendor adapter directly.

Existing invariants remain authoritative:

- eligibility is assessed through `PrintExecutionCapability`;
- `DISPATCHING` is persisted before adapter submission;
- `dispatch_id` is the printer-side idempotency identity;
- receipt-bearing jobs are never blindly resubmitted;
- an ambiguous adapter outcome becomes durable `INDETERMINATE`;
- `INDETERMINATE` is returned as queue resource state, not hidden behind a generic retryable HTTP error.

There is **no generic retry endpoint**.

A later explicit dispatch attempt after a pre-start failure is permitted only when the persisted queue error is marked retryable and no receipt exists. `DISPATCHING`, `INDETERMINATE`, receipt-bearing failures and non-retryable failures are rejected.

### 5. Reconciliation is explicit

The reconciliation endpoint is:

```text
POST /api/v1/queue/{queueId}/reconcile
Authorization: Bearer <command credential>
Idempotency-Key: <opaque key>
Content-Type: application/json
```

Request examples:

```json
{ "accepted": false }
```

or:

```json
{
  "accepted": true,
  "vendorJobId": "optional-vendor-job-id",
  "acceptedAt": "2026-09-04T13:00:00Z"
}
```

Only `DISPATCHING` or `INDETERMINATE` entries may be reconciled on first execution.

`accepted: false` returns the queue entry to `PENDING` without inventing a printer receipt. `accepted: true` creates the durable accepted receipt using the existing queue reconciliation contract.

### 6. HTTP replays are checked before current queue state

A completed `Idempotency-Key` replay must return the same logical result even if the queue has since advanced from `ACCEPTED` to `PREPARING`, or from `INDETERMINATE` to `PENDING` after reconciliation.

For that reason the single-process runtime installs a queue command guard around dispatch/reconcile. Inside one async critical section it:

1. authenticates the command identity;
2. looks up any durable HTTP idempotency record;
3. rejects a changed request fingerprint;
4. returns the current durable queue resource for a completed replay without invoking `QueueService.dispatch()` or reconciliation again;
5. rejects unresolved `STARTED` replays as `reconciliation_required`;
6. otherwise allows the command handler to execute.

The same critical section prevents two concurrent HTTP requests with different idempotency keys from racing the printer submission boundary in the current single-process runtime.

This guard is not a distributed lock. A future multi-worker/multi-node runtime requires a database-backed command lease/CAS design before horizontal command execution is enabled.

### 7. Command audit is durable and secret-free

Authenticated mutation routes produce append-only audit records in SQLite.

Audit fields:

- audit ID;
- request ID;
- principal ID when authenticated;
- action;
- target resource identity when known;
- SHA-256 digest of `Idempotency-Key`, never the raw key;
- outcome (`accepted`, `completed`, `conflict`, `denied`, `failed`);
- normalized error code when present;
- UTC timestamp.

The audit middleware writes an `accepted` record before an authenticated command side effect is allowed. If that preflight audit write fails, the command fails closed with `503 audit_unavailable` and is not executed.

Terminal audit failure does not replace an already-executed command response with a generic error, because doing so could encourage an unsafe client retry. The durable preflight record remains evidence that the request crossed the command boundary.

Bearer credentials, printer access codes and raw idempotency keys are not audit fields.

## API status codes

Queue/artifact commands continue ADR 0004 normalized error semantics.

Important mappings include:

- `400 invalid_request` — malformed UUID/JSON/header/selection/binding;
- `400 artifact_hash_mismatch` — body does not match the declared digest;
- `401 unauthorized` — missing/invalid command credential;
- `404 artifact_not_found`, `printer_not_found`, `queue_not_found`;
- `409 idempotency_conflict` — same key, changed fingerprint;
- `409 queue_reconciliation_required` — ambiguous queue state cannot be blindly dispatched;
- `409 queue_not_retryable` — failed pre-start attempt is not marked retryable;
- `413 artifact_too_large`;
- `415 unsupported_media_type`;
- `503 command_api_disabled` or `audit_unavailable`.

## Deployment consequences

- `/data/artifacts` must live on the same persistent volume as the runtime state for the current Docker/Umbrel deployment model.
- SQLite command audit and command-idempotency tables live in `/data/foxforge.sqlite3`.
- Artifact bytes are not stored inside SQLite.
- The design is compatible with Linux `amd64` and `arm64`; it has no architecture-specific dependency.
- No new cloud service is required.

## Not included in this phase

- browser UI for selecting/uploading a file and starting a print;
- common pause/resume/cancel commands;
- deep Bambu print options beyond existing `PrintExecutionRequest` selection/material bindings;
- artifact garbage collection/retention policy;
- multipart uploads or resumable chunk protocols;
- multi-process/distributed command execution;
- physical X2D, AMS 2 Pro, Ender-3 V3 KE/OpenKE validation.

## Acceptance criteria

- public queue commands never accept a server filesystem path;
- upload is authenticated, streamed, bounded and SHA-256 verified;
- staged artifacts survive store recreation/restart;
- duplicate content upload does not create duplicate files;
- enqueue requires durable HTTP idempotency and resolves only server-owned artifacts;
- same-key enqueue replay does not create another queue entry;
- changed enqueue payload under the same key returns `409 idempotency_conflict`;
- dispatch never bypasses `QueueService` or typed `PrintExecutionCapability`;
- same-key dispatch replay never increments printer start count;
- an `INDETERMINATE` dispatch cannot be submitted with a new key until reconciliation;
- same-key `INDETERMINATE` dispatch replay returns the existing queue resource without resubmission;
- reconciliation replay remains idempotent after the queue state changes;
- concurrent HTTP dispatch/reconcile commands are serialized in the single-process runtime;
- authorized mutations have preflight and terminal audit evidence;
- audit persistence never stores bearer tokens or raw idempotency keys;
- existing read API remains backward compatible;
- backend formatting/lint/test gates pass on Python 3.12 and 3.13;
- physical printer validation is not claimed by software-only tests.

## Follow-up

1. add browser-safe file selection/upload/enqueue flow using the existing trusted browser session boundary;
2. add artifact retention/garbage-collection policy after queue references and release semantics are defined;
3. implement common pause/resume/cancel only after a common typed control capability is designed;
4. validate the complete upload/dispatch/reconciliation path on physical X2D and OpenKE/Moonraker hardware;
5. replace the single-process async command guard with a durable lease/CAS mechanism before enabling multi-worker command execution.
