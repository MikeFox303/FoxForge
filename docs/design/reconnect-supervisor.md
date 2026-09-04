# Reconnect supervisor

Status: stabilization contract for AUD-012

## Context

FoxForge previously retried disconnected printers in one serial loop. A slow or hung `connect()` for one printer could therefore delay every printer after it in `fleet.printer_ids`, which is unacceptable for mixed-vendor farms and unreliable LAN endpoints.

Reconnect orchestration belongs in the runtime layer. `FleetService` remains the vendor-neutral collection/lifecycle API and printer adapters remain responsible for their own transport handshakes.

## Decision

The runtime maintains one reconnect worker per current printer ID.

Each worker:

- acts only while its printer remains in the dynamic fleet;
- retries only when the normalized snapshot is `DISCONNECTED`;
- resets failure backoff after a conclusive recovery;
- uses exponential retry delay starting from `reconnect_seconds`;
- caps delay at eight times the base interval;
- applies bounded ±20% jitter to failed retry delays;
- exits when its printer is removed.

A shared semaphore limits concurrent `connect()` calls to four. This prevents reconnect storms while still ensuring that one slow endpoint cannot serialize the entire fleet.

The coordinator reconciles worker membership at a bounded discovery interval (`min(reconnect_seconds, 1 second)`) so printers added through live configuration management join reconnect supervision without a process restart.

## Safety and fairness

- Reconnect workers call only the common `FleetService.connect()` contract; they contain no Bambu/Moonraker branching.
- A worker rechecks both fleet membership and normalized connection state after acquiring the global semaphore, avoiding stale queued connect attempts.
- Cancellation always propagates and runtime shutdown cancels/gathers all per-printer workers.
- `FleetPrinterNotFoundError` is a normal worker-exit condition during concurrent printer removal.
- A failed printer receives its own backoff and cannot increase another printer's retry delay.
- The semaphore bounds network pressure but does not impose ordering semantics on vendors.

## Acceptance criteria

- A blocked connect for one printer does not prevent another printer from recovering when semaphore capacity remains.
- Concurrent connect operations never exceed the configured global limit.
- Failed attempts use exponential bounded backoff and deterministic jitter math is unit-tested.
- A printer that fails transiently can recover without restarting the supervisor.
- A printer added to the live fleet receives a reconnect worker without restarting FoxForge.
- Removing/cancelling workers does not leak tasks.
- Existing backend, container, browser and security gates remain green.
