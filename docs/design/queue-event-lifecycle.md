# Queue event-driven print lifecycle

- **Status:** Phase 9 implementation candidate
- **Related ADR:** [ADR 0001: PrinterAdapter architecture](../adr/0001-printer-adapter-architecture.md)
- **Related queue design:** [Queue dispatch and durable idempotency](queue-dispatch.md)
- **Date:** 2026-09-04

## Context

Phase 4 made print dispatch durable and safe across process restarts. A queue entry is persisted as `DISPATCHING` before the adapter side effect, confirmed starts become `ACCEPTED`, and ambiguous starts become `INDETERMINATE` until explicitly reconciled.

That protected the start boundary but stopped tracking the queue entry after acceptance. Both Bambu and Moonraker adapters already emit normalized `JOB_STATE_CHANGED` events through `FleetService`, so the queue can track the remote job lifecycle without importing vendor-specific state.

## Decision

Extend `QueueEntryState` with normalized post-dispatch lifecycle states:

```text
ACCEPTED
  -> PREPARING
  -> PRINTING <-> PAUSED
  -> COMPLETED | FAILED | CANCELLED
```

`QueueService` subscribes to `FleetService.events()` and consumes only common `PrinterEventKind.JOB_STATE_CHANGED` events carrying `ActiveJobSnapshot`.

The queue never imports Bambu or Moonraker types.

## Job identity rule

Automatic lifecycle tracking requires a confirmed `PrintDispatchReceipt.vendor_job_id` and a matching `ActiveJobSnapshot.vendor_job_id`.

FoxForge deliberately does **not** guess by filename, requested name, printer id alone, or "the only active queue item". If the adapter cannot supply a stable remote job identity, the queue remains at its last confirmed state until a safer correlation mechanism is designed.

This prevents an externally started print from accidentally completing or failing a FoxForge queue entry.

## `INDETERMINATE` rule

`INDETERMINATE` entries are never auto-reconciled from ordinary job-state events because they intentionally have no confirmed receipt.

Even if a later event appears to resemble the submitted job, the queue does not silently convert that ambiguity into success. Explicit reconciliation remains required.

## Runtime tracking

`QueueService.start()`:

1. subscribes to normalized fleet events;
2. waits until the subscription is active;
3. reconciles already persisted accepted/running entries against current common printer snapshots.

`dispatch()` starts tracking lazily before invoking a side effect, while the eventual application composition root should call `QueueService.start()` during startup so restored durable entries resume lifecycle observation even when no new dispatch occurs.

`QueueService.aclose()` stops only the queue's event subscription; it does not own or close `FleetService`.

## Restart behavior

A restarted process can restore an `ACCEPTED`, `PREPARING`, `PRINTING`, or `PAUSED` entry from SQLite. On `QueueService.start()`, the current `PrinterSnapshot.active_job` is compared by confirmed `vendor_job_id`.

If it matches, the durable entry advances to the current normalized state. If it does not match or the printer reports no stable job id, FoxForge leaves the entry unchanged rather than guessing.

## Ordering and replay safety

Lifecycle transitions are monotonic except for the legitimate `PRINTING <-> PAUSED` resume cycle.

Examples that are rejected as stale/backward transitions:

- `PRINTING -> PREPARING`
- `PAUSED -> PREPARING`
- `COMPLETED -> PRINTING`
- `FAILED -> PRINTING`
- `CANCELLED -> PRINTING`

Terminal states do not regress. Duplicate observations are idempotent and may only advance the queue's observation timestamp.

## Receipt semantics

A dispatch receipt remains attached throughout the confirmed remote lifecycle:

- `ACCEPTED`
- `PREPARING`
- `PRINTING`
- `PAUSED`
- `COMPLETED`
- `CANCELLED`
- remotely observed `FAILED`

`FAILED` remains dual-purpose:

- without a receipt: dispatch/contract failure before a confirmed remote job;
- with a receipt: the confirmed remote print later failed.

This preserves the original remote job identity for post-print accounting and future inventory workflows.

## Persistence

No SQLite schema shape change is required for Phase 9 because `QueueEntryState` is already serialized as a string inside the versioned queue payload and the receipt is already durable.

The new state values therefore round-trip through the existing `SQLiteQueueStore` representation. Tests must cover at least one terminal post-dispatch state to guard that assumption.

## Acceptance criteria

1. Queue lifecycle uses only normalized `FleetService` events and common `ActiveJobSnapshot`/`JobState` types.
2. A confirmed queue entry advances through preparing, printing, pause/resume and completion states.
3. Unrelated `vendor_job_id` values cannot mutate a queue entry.
4. Terminal states cannot regress on stale/replayed events.
5. `QueueService.start()` reconciles a restored accepted entry from the current normalized printer snapshot.
6. `INDETERMINATE` entries are never auto-resolved by ordinary job events.
7. Existing dispatch idempotency and pre-submit crash semantics remain unchanged.
8. SQLite persistence round-trips the new lifecycle states and retained receipt.
9. Ruff, architecture checks, and the full suite pass on Python 3.12 and Python 3.13.

## Deferred

Phase 9 does not add:

- automatic retry/backoff;
- printer selection/scheduling across a farm;
- cancellation commands;
- inventory reservation/consumption;
- heuristic job matching when no stable vendor job id exists.

Those should build on the now-durable remote lifecycle rather than weakening the dispatch safety boundary.
