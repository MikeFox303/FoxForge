# Queue dispatch and durable idempotency

- **Status:** implementation design
- **Date:** 2026-09-03
- **Related:** ADR 0001, [Printer contracts v1](printer-contracts.md), [AdapterRegistry and FleetService](fleet-service.md)

## Purpose

Phase 4 moves automated print submission into a FoxForge application service. The queue must remain vendor-neutral and must survive process restarts without accidentally starting the same print twice.

The dependency path is:

```text
QueueService
    -> FleetService
        -> PrintExecutionCapability
            -> concrete adapter
```

Queue code never imports `BambuAdapter`, a future `MoonrakerAdapter`, MQTT/FTP clients, or vendor DTOs.

## Durable idempotency boundary

`PrintExecutionCapability` provides adapter-instance idempotency. The queue owns the stronger process-restart guarantee.

For every queue entry, FoxForge persists:

- stable `queue_id`;
- target `printer_id`;
- stable `dispatch_id`;
- immutable print request/artifact fingerprint;
- assessment and blockers when available;
- current dispatch state;
- dispatch attempt count and timestamp;
- accepted receipt or normalized error.

`dispatch_id` is created and stored before the queue calls either `assess()` or `submit()`.

Immediately before calling `submit()`, the entry is durably moved to `DISPATCHING` and the attempt count is incremented. This ordering creates a conservative crash boundary:

```text
persist DISPATCHING
        |
        v
capability.submit(...)
        |
        +--> receipt -> persist ACCEPTED
        |
        +--> normalized failure -> persist FAILED
        |
        +--> INDETERMINATE -> persist INDETERMINATE
```

If the process dies after `DISPATCHING` was written but before a receipt/failure was persisted, the next process must assume a side effect may have occurred. It must not blindly call `submit()` again.

## Queue states

```text
PENDING
  | assess eligible
  v
DISPATCHING -------> ACCEPTED
  |                     ^
  | definite error      | reconciliation proves accepted
  v                     |
FAILED                  |
                        |
DISPATCHING/INDETERMINATE
  |
  | reconciliation proves not accepted
  v
PENDING

PENDING/FAILED -- assess blocked --> BLOCKED
BLOCKED -------- reassess ---------> PENDING or BLOCKED
```

### `PENDING`

The request is persisted and may be assessed/dispatched.

### `BLOCKED`

The latest side-effect-free assessment is ineligible, or the printer does not currently expose `PrintExecutionCapability` v1. A later explicit dispatch attempt may reassess the entry.

### `DISPATCHING`

The queue persisted the pre-submit crash boundary and then attempted or was about to attempt the side effect. A persisted `DISPATCHING` entry discovered after restart requires reconciliation before any retry.

### `ACCEPTED`

A validated `PrintDispatchReceipt` is persisted. Calling queue dispatch again returns the persisted entry and does not call the adapter.

### `INDETERMINATE`

The adapter reported that the vendor may have accepted the start but the result could not be proven. Automatic retry is forbidden until reconciliation.

### `FAILED`

The adapter returned a definite normalized non-indeterminate failure. The error and retryability metadata are persisted. FoxForge v1 does not implement an automatic retry loop; a later explicit dispatch call reassesses and reuses the same `dispatch_id`.

## Reconciliation

`QueueService.resolve_reconciliation()` records an outcome established by a trusted reconciliation mechanism.

The v1 method deliberately does not inspect Bambu/Moonraker raw state itself. The caller must first establish one of two facts:

1. **accepted** — the previous dispatch is known to correspond to an accepted/current vendor job. The queue persists an `ACCEPTED` receipt without another submit.
2. **not accepted** — the previous dispatch is known not to have taken effect. The queue returns to `PENDING`; a later explicit dispatch can safely reuse the same `dispatch_id`.

Automatic generic reconciliation based on printer/job events is deferred until FoxForge has enough cross-vendor evidence to define reliable matching rules. False certainty is more dangerous than requiring explicit reconciliation.

## Storage boundary

`QueueService` depends on a synchronous `QueueStore` protocol:

```python
create(entry)
save(entry)
get(queue_id)
list()
```

Two implementations exist in Phase 4:

- `InMemoryQueueStore` — deterministic tests/composition experiments only;
- `SQLiteQueueStore` — durable single-container storage for the current Docker/ARM64/Umbrel architecture.

The SQLite implementation stores a versioned JSON payload per entry. This is intentionally simple for the first application slice while still providing real restart durability. A later schema migration may normalize queue columns without changing the application service contract.

## Receipt validation

Before persisting `ACCEPTED`, QueueService verifies that the returned receipt has the same:

- `dispatch_id`;
- artifact SHA-256 fingerprint.

A mismatch is recorded as `FAILED` with `INTERNAL_ADAPTER_ERROR`; common queue code never branches on vendor codes.

## Out of scope for Phase 4

This slice does not yet implement:

- automatic scheduling among multiple pending jobs;
- printer selection/scoring;
- automatic retry/backoff;
- automatic event-driven transition from accepted to printing/completed;
- generic reconciliation heuristics;
- cancellation/reordering;
- REST/API endpoints;
- inventory reservations;
- distributed workers or multi-process write coordination.

These can be layered on the persisted queue state after the dispatch safety boundary is proven.

## Acceptance criteria

Phase 4 is complete when:

1. Queue code imports no concrete vendor adapter or vendor DTO.
2. `dispatch_id` is persisted before any adapter assessment/submission.
3. The queue persists `DISPATCHING` before calling `submit()`.
4. Re-dispatching an `ACCEPTED` entry never calls `submit()` again.
5. `INDETERMINATE` and persisted `DISPATCHING` entries reject blind retry.
6. Reconciliation can mark an uncertain dispatch accepted without a second submit.
7. Reconciliation can prove non-acceptance and allow an explicit retry with the original `dispatch_id`.
8. A printer without `PrintExecutionCapability` is blocked through common capability discovery, not vendor branching.
9. SQLite persistence preserves accepted and indeterminate safety semantics across new store/adapter instances.
10. Ruff and the full suite pass on Python 3.12 and 3.13.
