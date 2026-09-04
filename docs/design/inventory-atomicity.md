# Atomic inventory ledger mutations

Status: stabilization design for AUD-010.

## Problem

Before this change `InventoryService` read the spool, read all adjustments, validated the proposed next balance, and only then called `InventoryStore.append_adjustment`. Those reads and the final SQLite INSERT were separate transactions. Two workers could therefore both observe the same valid balance and both commit deductions that were invalid in combination.

Automatic filament accounting cannot safely build on that boundary.

## Decision

The persistence boundary owns the complete adjustment mutation. `InventoryStore.append_adjustment` returns `AdjustmentWriteResult` containing the stored adjustment and whether a new row was created.

For SQLite, one adjustment is linearized by `BEGIN IMMEDIATE`. While holding the writer reservation, the store:

1. checks the idempotency key;
2. returns the already stored adjustment for a replay without adding a second ledger row;
3. loads the target spool and rejects missing/archived spools;
4. loads the current ledger and computes the balance with exact `Decimal` values decoded from FoxForge payloads;
5. validates `0 <= next_remaining <= initial_filament_mass_g`;
6. inserts the adjustment;
7. commits.

Any balance/archive/missing/conflict failure rolls the transaction back. A second writer cannot perform its balance check until the first writer has committed or rolled back, so the outcome is equivalent to a serial writer order.

The in-memory test store provides the same contract behind an `RLock` so application tests do not model weaker semantics than production.

## Idempotency

The idempotency lookup is inside the same atomic writer transaction as balance validation and INSERT. Concurrent delivery of the same completion identity therefore produces one durable adjustment. Both callers receive the same stored adjustment.

If an existing idempotency key describes different spool/kind/delta/note data, `InventoryService` still raises `InventoryIdempotencyConflictError`.

Realtime `balance_changed` is published only when `AdjustmentWriteResult.created` is true. Idempotent replay does not emit a false second mutation notification.

## Application boundary

`InventoryService` continues to own command intent and user-facing errors, but it no longer performs a pre-write balance read. Store errors are mapped to `SpoolNotFoundError`, `ArchivedSpoolError`, and `InventoryBalanceError`.

Read-only `balance()` remains an application read model and may run outside a writer transaction; it is not used to authorize a ledger mutation.

## Acceptance evidence

Automated SQLite concurrency tests cover:

- two simultaneous deductions that would overdraw only in combination: exactly one commits;
- concurrent duplicate completion with the same idempotency identity: one row, same result to both callers;
- manual positive correction racing automatic consumption: final state must match one valid serialized ordering;
- restart replay returning the original adjustment without another deduction;
- insufficient balance rejection leaving the ledger unchanged.

This resolves the persistence race prerequisite for P3, but does not by itself unfreeze P3. The remaining audit/deployment and operator-workflow gates still apply.
