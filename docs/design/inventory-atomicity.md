# Atomic inventory ledger mutations

- **Status:** implemented
- **Updated:** 2026-09-06
- **Related:** AUD-010, [inventory foundation](inventory-foundation.md), [SQLite inventory](inventory-sqlite.md)

## Problem

A ledger balance check performed outside the same transaction as the adjustment insert can race: two writers may both see a valid old balance and commit a combined invalid result.

## Decision

The persistence boundary owns the complete adjustment mutation. `InventoryStore.append_adjustment` returns the stored adjustment plus whether a new row was created.

For SQLite, `BEGIN IMMEDIATE` linearizes one adjustment while the store:

1. checks durable idempotency;
2. returns the original row for a same-request replay;
3. loads/validates the spool;
4. computes current exact-`Decimal` balance;
5. validates the proposed balance range;
6. inserts the adjustment;
7. commits.

Any conflict/balance/archive/missing-spool failure rolls back. The in-memory test store provides equivalent semantics behind a lock.

## Idempotency and events

The idempotency check is inside the same writer transaction. Concurrent duplicate completion identities therefore create one ledger row and return one logical result.

Changed request data under an existing idempotency key conflicts.

Realtime `balance_changed` publishes only when a new row was created; replay does not create a false second mutation notification.

## Boundary

`InventoryService` owns command intent/user-facing errors but does not authorize a mutation from a stale pre-read balance. Read-only `balance()` remains a projection, not a write guard.

This atomicity is a prerequisite for future automatic accounting but does not unfreeze P3 by itself.

## Acceptance evidence

Tests cover concurrent overdraw, duplicate idempotency, correction-vs-consumption serialization, restart replay and rejected insufficient-balance mutations leaving the ledger unchanged.
