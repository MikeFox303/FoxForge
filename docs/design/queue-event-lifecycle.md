# Queue event-driven print lifecycle

- **Status:** implemented normalized lifecycle tracking
- **Updated:** 2026-09-06
- **Related:** [queue dispatch](queue-dispatch.md), [realtime application events](realtime-events.md)

## Purpose

After a start is confirmed, the durable queue follows the remote print using normalized fleet/job events without importing vendor state.

```text
ACCEPTED
  -> PREPARING
  -> PRINTING <-> PAUSED
  -> COMPLETED | FAILED | CANCELLED
```

## Exact job identity

Automatic lifecycle tracking requires the confirmed dispatch receipt's `vendor_job_id` to match the printer snapshot/event's active `vendor_job_id`.

FoxForge does not guess by filename, printer ID alone or "the only active queue item". An externally started job must not accidentally complete/fail a FoxForge queue entry.

## `INDETERMINATE`

An uncertain start has no confirmed receipt and is never auto-reconciled from ordinary job-state telemetry. Explicit reconciliation remains required.

## Restart behavior

On startup, persisted accepted/running entries are reconciled against current normalized printer snapshots by exact confirmed vendor job identity. If identity cannot be established, the queue keeps the last durable state rather than inventing certainty.

## Ordering

Terminal states do not regress. Duplicate observations are idempotent. Legitimate `PRINTING <-> PAUSED` transitions remain allowed; stale backward transitions such as `PRINTING -> PREPARING` are rejected.

## Receipt semantics

The confirmed receipt remains attached through accepted/preparing/printing/paused/completed/cancelled and remotely observed failed states. This preserves the exact remote job identity for audit/accounting/reconciliation consumers.

## Current surrounding functionality

The original lifecycle slice has since been extended by:

- safe retry policy for receipt-free pre-start failures;
- common exact-job Pause/Resume/Cancel;
- SSE application invalidations for browser cache refresh;
- durable inventory workflows (automatic P3 consumption still frozen).

## Acceptance criteria

- queue lifecycle consumes normalized fleet/job contracts only;
- unrelated job IDs cannot mutate an entry;
- restart reconciliation uses exact confirmed job identity;
- terminal states do not regress;
- `INDETERMINATE` is never auto-resolved from ordinary events;
- receipt remains durable throughout the confirmed remote lifecycle.
