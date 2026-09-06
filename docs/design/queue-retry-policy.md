# Queue retry and single-pass runner policy

- **Status:** implemented safe retry foundation
- **Updated:** 2026-09-06
- **Related:** [queue dispatch](queue-dispatch.md), [queue event lifecycle](queue-event-lifecycle.md)

## Purpose

Retry logic must not weaken the durable start boundary. A failed-looking entry is not automatically safe to submit again.

## Safe retry eligibility

A retryable start attempt requires all applicable conditions:

- state represents a definite pre-start failure;
- no dispatch receipt exists;
- normalized error is explicitly retryable;
- at least one prior attempt exists;
- configured backoff has elapsed;
- maximum attempt count is not exhausted.

The original durable `dispatch_id` remains attached across safe retry attempts.

## Never auto-retry

The runner never redispatches:

- persisted `DISPATCHING` after crash/ambiguity;
- `INDETERMINATE`;
- any receipt-bearing lifecycle state;
- non-retryable pre-start failure;
- exhausted retryable failure.

Blocked entries may be reassessed because capability assessment is side-effect-free.

## Backoff

The policy uses bounded exponential backoff. Defaults remain conservative and injectable so deployments/tests can change timing without changing queue safety semantics.

Retry timing is derived from durable attempt/error timestamps/state, so restart does not reset the safety boundary.

## Single-pass runner

`QueueRunner.run_once()` processes at most one candidate per printer per pass and serializes concurrent passes in one runtime instance.

This is not a distributed lease. FoxForge still targets one active backend process/container. Persistent farm scheduling and multi-worker execution require an explicit durable lease/CAS design before multiple writers can dispatch concurrently.

## Current scope

Implemented:

- deterministic safe retry assessment;
- bounded backoff/attempt limit;
- side-effect-free reassessment of blocked jobs;
- one-entry-per-printer pass;
- same-dispatch-identity retry;
- no retry of receipt/ambiguity states.

Deferred:

- persistent farm priority/deadline scheduler;
- unassigned-job printer selection/scoring;
- multi-process distributed dispatch leases;
- automatic generic reconciliation of ambiguous starts.

## Acceptance criteria

- retry never crosses `INDETERMINATE`/receipt boundaries;
- retry does not generate a fresh printer-side dispatch identity;
- backoff/attempt limits survive restart;
- blocked reassessment remains side-effect-free;
- one runner pass cannot start multiple jobs on one printer;
- common retry code has no vendor imports.
