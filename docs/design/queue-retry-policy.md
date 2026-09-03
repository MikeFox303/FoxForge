# Queue retry and single-pass runner policy

- **Status:** Phase 10 implementation candidate
- **Related ADR:** [ADR 0001: PrinterAdapter architecture](../adr/0001-printer-adapter-architecture.md)
- **Related designs:** [Queue dispatch and durable idempotency](queue-dispatch.md), [Queue event-driven print lifecycle](queue-event-lifecycle.md)
- **Date:** 2026-09-04

## Context

FoxForge already has two safety boundaries that retry logic must not weaken:

1. Phase 4 persists `DISPATCHING` before any print-start side effect and converts ambiguous starts to `INDETERMINATE`.
2. Phase 9 retains a confirmed dispatch receipt throughout the remote job lifecycle.

A retry mechanism therefore cannot mean "try every failed-looking queue entry again." It must distinguish a known pre-start failure from an ambiguous or already accepted print.

## Decision

Introduce two application-level components:

- `QueueRetryPolicy` — deterministic exponential backoff and maximum attempt count;
- `QueueRunner` — one explicit `run_once()` scheduling pass over printer-pinned queue entries.

Phase 10 deliberately does **not** create a permanent background loop. A future server/composition root may invoke `run_once()` from a timer, while tests and administrative tooling can invoke the same deterministic operation directly.

## Safe retry eligibility

Automatic retry is allowed only when all of these are true:

- queue state is `FAILED`;
- there is no dispatch receipt;
- a normalized `QueueDispatchError` exists;
- `error.retryable` is `True`;
- at least one prior dispatch attempt exists;
- the configured backoff delay has elapsed;
- `attempt_count < max_attempts`.

This identifies a failure that the adapter has explicitly classified as safe to retry before a confirmed print start.

## States the runner never retries

The runner never redispatches:

- `DISPATCHING` — process/crash ambiguity must be reconciled;
- `INDETERMINATE` — the printer may already have accepted the start;
- any entry carrying a receipt, including `ACCEPTED`, `PREPARING`, `PRINTING`, `PAUSED`, `COMPLETED`, `CANCELLED`, or remotely observed `FAILED`;
- a non-retryable `FAILED` entry;
- a retryable failure whose maximum attempt count is exhausted.

The same `dispatch_id` remains attached to a retryable entry across attempts. Retry policy never creates a replacement request merely to bypass idempotency.

## Backoff

For attempt count `n >= 1`:

```text
delay = min(
    initial_delay * backoff_multiplier ** (n - 1),
    max_delay,
)
```

The default policy is:

```text
initial delay: 5 seconds
multiplier:    2
maximum delay: 300 seconds
maximum attempts: 5 (including the first attempt)
```

Policy is injected into `QueueRunner`, allowing deployments and later configuration to choose more conservative values without changing queue state semantics.

## Pending and blocked entries

`PENDING` entries are eligible immediately.

`BLOCKED` entries may be reassessed because `PrintExecutionCapability.assess()` is side-effect-free. A blocked entry that becomes eligible can then dispatch normally. Reassessment does not increment `attempt_count`; only reaching the durable `DISPATCHING` boundary does.

## One entry per printer per pass

A single `run_once()` processes at most one candidate entry for each printer id, preserving queue order.

This avoids a pass immediately attempting multiple jobs against the same printer. A later farm scheduler may implement richer priority/fairness rules above this boundary.

## Concurrent calls

One `QueueRunner` instance serializes concurrent `run_once()` calls with an async lock. This closes the normal single-process timer race where two scheduler ticks overlap.

This is **not** a distributed lock. FoxForge's current v1 deployment target is a single backend/container. If queue execution is later split across multiple processes or replicas, durable compare-and-set/lease semantics must be added at the store layer before enabling multiple active runners.

## Persistence

Phase 10 requires no new queue columns or SQLite payload fields. Retry timing is derived from already durable values:

- `attempt_count`;
- `last_attempt_at`;
- `QueueDispatchError.retryable`.

Therefore a process restart preserves enough information to calculate the next safe retry time, provided the deployment uses the same configured retry policy.

## Acceptance criteria

1. A retryable pre-start failure is not retried before its backoff deadline.
2. When due, it retries with the same `dispatch_id` and increments `attempt_count` only through normal QueueService dispatch semantics.
3. `INDETERMINATE` is never retried automatically.
4. Non-retryable failures are never retried automatically.
5. Exhausted retryable failures are not retried.
6. Receipt-bearing remote failures are never mistaken for retryable dispatch failures.
7. Blocked entries can be safely reassessed without counting a dispatch attempt until a real submit is attempted.
8. At most one entry per printer is processed in one pass.
9. Concurrent `run_once()` calls on one runner are serialized.
10. QueueRunner depends only on application/common queue contracts and adds no vendor imports.
11. Ruff, architecture checks, and the full suite pass on Python 3.12 and Python 3.13.

## Deferred

Phase 10 does not implement:

- a permanent scheduler timer/background task;
- unassigned jobs or automatic farm printer selection;
- priorities/deadlines;
- multi-process leases or distributed queue execution;
- automatic reconciliation of `DISPATCHING`/`INDETERMINATE`;
- inventory reservations.

Those features can build on the deterministic `run_once()` policy without changing the core print-start safety rules.
