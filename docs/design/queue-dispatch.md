# Queue dispatch and durable idempotency

- **Status:** implemented durable queue contract
- **Updated:** 2026-09-08
- **Related:** [queue event lifecycle](queue-event-lifecycle.md), [retry policy](queue-retry-policy.md), [queue command API](queue-command-api.md)

## Purpose

Queue dispatch is vendor-neutral and restart-safe. Common code reaches printers only through `FleetService` and `PrintExecutionCapability`.

```text
QueueService -> FleetService -> PrintExecutionCapability -> adapter
```

Optional common policies may participate through queue-owned protocols. Queue code does not import inventory/accounting implementations and does not decide which provider enables a policy.

## Durable start boundary

Every queue entry persists stable queue/printer/dispatch identity, artifact/request fingerprint, state, attempt metadata, assessment, receipt and normalized error.

Before any potentially side-effecting submit, FoxForge durably writes `DISPATCHING` and increments the attempt count.

```text
persist DISPATCHING
        |
capability.submit(...)
        +--> receipt -> ACCEPTED
        +--> definite normalized failure -> FAILED
        `--> uncertain remote outcome -> INDETERMINATE
```

A process restart that finds `DISPATCHING` must assume a start may have happened and cannot blindly submit again.

## Optional pre-dispatch policy boundary

A common `QueuePreDispatchGate` may add fail-closed application policy without becoming part of printer routing or adapter code. The ordering is normative:

```text
immutable request / artifact
        -> fresh material routing compilation
        -> printer capability assessment
        -> optional QueuePreDispatchGate
        -> persist DISPATCHING
        -> capability.submit(...)
```

There is no await point between the synchronous policy decision and the durable `DISPATCHING` write. In the current single-process runtime this prevents another event-loop request from interleaving between the final policy check and the queue-owned start boundary.

The gate receives the already-compiled request. It must not replace the routing compiler, infer provider/model semantics, or perform a printer side effect. A blocker is normalized back into the existing `PrintExecutionAssessment` model and leaves `attempt_count` unchanged.

Provider enablement is explicit composition-root policy. Constructing an ordinary `QueueService` without a gate preserves the original behavior.

## Optional lifecycle observer boundary

A common `QueueLifecycleObserver` may observe a queue entry only after that state has been durably saved. QueueService also replays restored entries through the same per-entry observer hook during startup, after reconciling current printer snapshots.

Observer failures are logged and isolated per queue entry. They cannot roll back the already-durable queue state or terminate the normalized fleet event tracker. This is important for secondary workflows such as inventory settlement: a failed secondary update remains recoverable on restart without corrupting the queue lifecycle.

## Identities

`dispatch_id` is the durable printer-side logical start identity. It is distinct from the HTTP `Idempotency-Key` used by public commands.

Confirmed receipts are retained through the remote job lifecycle and prevent redispatch.

## Queue states

The current durable lifecycle includes:

```text
PENDING
BLOCKED
DISPATCHING
ACCEPTED
PREPARING
PRINTING
PAUSED
COMPLETED
CANCELLED
INDETERMINATE
FAILED
```

`FAILED` without a receipt may describe a pre-start dispatch failure, but absence of a receipt alone does not prove that no remote side effect occurred once `attempt_count > 0`. `FAILED` with a receipt describes a confirmed remote job that later failed; that receipt-bearing entry is never a retryable start.

## Reconciliation

Explicit reconciliation can establish that an uncertain dispatch was accepted or not accepted without guessing from filenames or printer identity alone.

- accepted -> persist/retain receipt, never submit again;
- proven not accepted -> return to a safe dispatchable state according to the queue contract;
- unresolved ambiguity remains reconciliation-required.

Ordinary job-state events do not silently convert an `INDETERMINATE` entry into success.

## Persistence

`SQLiteQueueStore` provides current durable single-container storage. In-memory storage remains a test utility.

Queue safety survives process restart: accepted receipts and ambiguous dispatch states are restored before any new attempt can occur.

## Evolution since the original dispatch slice

Now implemented above this core boundary:

- normalized post-acceptance event lifecycle tracking;
- safe retry/backoff for explicitly retryable receipt-free pre-start failures;
- public artifact/enqueue/dispatch/reconciliation APIs;
- browser-safe file staging/queue workflow;
- common job control as a separate exact-job capability;
- artifact retention/capacity safeguards;
- optional vendor-neutral pre-dispatch policy and lifecycle-observer seams.

Persistent farm scheduling and distributed command leases remain separate future work.

## Acceptance criteria

- queue code imports no vendor adapter/DTO and no concrete accounting implementation;
- fresh routing/assessment completes before any optional pre-dispatch gate;
- a gate blocker occurs before `DISPATCHING`, leaves `attempt_count` unchanged and causes no submit side effect;
- `DISPATCHING` persists before submit;
- receipt-bearing entries cannot be blindly redispatched;
- `INDETERMINATE` cannot be retried without reconciliation;
- restart preserves dispatch/receipt/ambiguity semantics;
- lifecycle-observer failure cannot terminate queue event tracking;
- safe retries reuse the durable logical dispatch identity;
- public HTTP command idempotency remains a separate boundary;
- physical start/control claims require real-device evidence.
