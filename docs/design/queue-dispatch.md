# Queue dispatch and durable idempotency

- **Status:** implemented durable queue contract
- **Updated:** 2026-09-06
- **Related:** [queue event lifecycle](queue-event-lifecycle.md), [retry policy](queue-retry-policy.md), [queue command API](queue-command-api.md)

## Purpose

Queue dispatch is vendor-neutral and restart-safe. Common code reaches printers only through `FleetService` and `PrintExecutionCapability`.

```text
QueueService -> FleetService -> PrintExecutionCapability -> adapter
```

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

`FAILED` without a receipt may describe a pre-start dispatch failure. `FAILED` with a receipt describes a confirmed remote job that later failed; that receipt-bearing entry is never a retryable start.

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
- artifact retention/capacity safeguards.

Persistent farm scheduling and distributed command leases remain separate future work.

## Acceptance criteria

- queue code imports no vendor adapter/DTO;
- `DISPATCHING` persists before submit;
- receipt-bearing entries cannot be blindly redispatched;
- `INDETERMINATE` cannot be retried without reconciliation;
- restart preserves dispatch/receipt/ambiguity semantics;
- safe retries reuse the durable logical dispatch identity;
- public HTTP command idempotency remains a separate boundary;
- physical start/control claims require real-device evidence.
