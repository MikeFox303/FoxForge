# Command idempotency reservation ownership

Status: safety refinement for ADR 0004 command idempotency.

## Problem

A durable `STARTED` command record is not enough for a caller to decide whether it may execute the command side effect.

If `reserve()` returns only the stored record, these two cases are indistinguishable:

1. the current request atomically inserted a new `STARTED` reservation;
2. a retry/restart observed an already-existing `STARTED` reservation left by an earlier request whose outcome is not yet known.

Executing the side effect in both cases would defeat the purpose of command idempotency and could duplicate spool/queue/printer mutations after a client timeout or process restart.

## Decision

`CommandIdempotencyStore.reserve()` returns `CommandIdempotencyReservation`:

- `record` — the canonical stored record;
- `created=True` — this caller atomically created the durable reservation and is the only caller permitted to proceed to the side effect;
- `created=False` — this is a replay of an existing reservation and the caller must not execute the side effect again.

For a replay:

- existing `COMPLETED` records may return their stored logical result;
- existing `STARTED` records represent an unresolved command execution and must not be re-executed merely because a retry arrived;
- a changed request fingerprint remains a conflict.

The SQLite implementation determines ownership inside the same `BEGIN IMMEDIATE` transaction that checks/inserts the record. No preflight `get()` + later `reserve()` sequence is allowed because that would reintroduce a race.

## Acceptance criteria

- in-memory and SQLite stores expose the same ownership semantics;
- only the first reservation reports `created=True`;
- same-key/same-fingerprint replay reports `created=False`;
- ownership remains `False` after process/store restart;
- completed replay reports `created=False` and preserves the terminal record;
- changed request fingerprints still conflict;
- no command HTTP mutation is added by this refinement.
