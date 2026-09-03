# Inventory foundation

Status: Phase 11 design specification

Related: ADR 0001, `docs/design/printer-contracts.md`, `docs/design/queue-event-lifecycle.md`

## Context

FoxForge needs durable filament/spool inventory for mixed printer fleets while preserving the printer-domain rule that physical material state must not contain FoxForge inventory identifiers.

`MaterialSystemCapability` already exposes stable opaque physical slot identifiers such as an AMS tray or a Moonraker external-spool source. Inventory therefore owns the relationship between a FoxForge spool and a physical printer slot.

The web UI is being developed in parallel. Phase 11 intentionally introduces backend domain/application contracts only; it does not edit `frontend/`, root UI wiring, or public HTTP endpoints. This keeps the inventory model stable before the frontend mock gateway is replaced by a live API.

## Decision

Create an independent `domain.inventory` bounded context plus an application-level `InventoryService` and `InventoryStore` port.

Inventory remains independent from `domain.printers` and concrete adapters. The only cross-context identifiers persisted by the foundation are string values for `printer_id` and opaque `slot_id`.

## Spool model

A `Spool` owns inventory metadata:

- stable UUID `spool_id`;
- material family;
- initial filament mass in grams;
- optional manufacturer and product name;
- optional RGBA color;
- optional empty-spool mass;
- optional purchase date;
- created/updated timestamps;
- archive flag.

Mass values use `Decimal` rather than binary floating point so accounting and future API serialization do not accumulate float error.

`empty_spool_mass_g` is metadata and may be edited after spool creation. It is not mixed into `remaining_filament_mass_g`; the ledger tracks filament mass only.

## Immutable mass ledger

Remaining filament is derived from:

```text
initial_filament_mass_g + sum(adjustment.delta_filament_mass_g)
```

Adjustment kinds in Phase 11:

- `CONSUMPTION` — negative;
- `WASTE` — negative;
- `RETURN` — positive;
- `CORRECTION` — positive or negative.

A stored adjustment is immutable. Corrections create another ledger record instead of mutating history.

The service rejects any adjustment that would make remaining filament negative or exceed the spool's original filament mass.

## Idempotency

Every adjustment requires an `idempotency_key`.

The same key with the same spool, kind, delta and note returns the previously stored adjustment. The same key with materially different data raises `InventoryIdempotencyConflictError`.

Replay is checked before archive-state rejection. Therefore an already recorded completed-print consumption remains exactly-once replayable after the spool is later archived, while a genuinely new adjustment on an archived spool is rejected.

This is the foundation for a later queue-accounting worker to use a deterministic key derived from the durable queue/job identity without double-deducting after process restart or event replay.

## Physical assignments

`SpoolAssignment` represents:

```text
(spool_id) <-> (printer_id, slot_id)
```

Rules:

- one spool may be assigned to at most one physical slot;
- one physical slot may have at most one FoxForge spool assigned;
- assigning the same spool to the same slot is idempotent;
- moving a spool requires explicit unassignment first;
- archived spools cannot be assigned;
- an assigned spool must be unassigned before archive.

`slot_id` is opaque. Inventory must not infer AMS, CFS, tray indexes or Moonraker semantics from the string.

The printer adapter continues to report physical material state without `spool_id`.

## Store boundary

`InventoryStore` owns persistence primitives for:

- spool create/update/read/list;
- append-only adjustments and idempotency lookup;
- spool/slot assignments.

Phase 11 supplies `InMemoryInventoryStore` for deterministic contract tests. Durable SQLite persistence is the next isolated implementation slice so the public application model does not depend on SQLite details.

## UI coordination boundary

The parallel frontend may model inventory cards and material-slot presentation, but Phase 11 does not make frontend types authoritative.

The future HTTP API should expose DTOs derived from `InventoryService`, rather than allowing React mock types to leak into the Python domain. Conversely, the backend will not add vendor-specific UI fields simply to match a current mock screen.

Expected future UI-facing read models include:

- spool identity and metadata;
- initial/remaining/used filament mass;
- used fraction;
- current assignment (`printer_id`, `slot_id`) when present;
- archived state.

Mutation endpoints can later map to application operations such as add spool, update empty-spool mass, assign/unassign, archive, consume/waste/return/correct.

## Out of scope for Phase 11

- SQLite inventory persistence;
- automatic queue-completion consumption;
- material reservation before dispatch;
- parsing 3MF/G-code consumption estimates;
- matching detected RFID/tag identity to a FoxForge spool;
- pricing/cost accounting;
- frontend implementation or API transport;
- multi-process transactional locking.

## Acceptance criteria

- inventory domain imports no printer/vendor/application/infrastructure modules;
- no `spool_id` is added to `MaterialSystemCapability` snapshots;
- empty-spool mass is editable after creation;
- balance is deterministic from initial mass plus immutable adjustments;
- balance can never fall below zero or exceed initial filament mass;
- adjustment replay is idempotent and conflicting key reuse is rejected;
- recorded adjustment replay remains idempotent after later spool archive;
- one spool maps to at most one physical slot and a slot to at most one spool;
- moving an assigned spool requires explicit unassignment;
- archived spools reject new assignments and new adjustments;
- Bambu and Moonraker concepts do not appear in inventory production code;
- Python 3.12 and 3.13 CI passes.

## Required tests

- spool/value-model validation;
- `Decimal` mass accounting;
- consumption, waste, return and correction ledger semantics;
- duplicate adjustment replay;
- conflicting idempotency-key reuse;
- archived-spool replay safety;
- invalid over-consumption/over-return rejection;
- editable empty-spool mass;
- assignment idempotency and conflicts;
- explicit unassign-before-move/archive;
- architecture guard preventing printer/vendor imports in `domain.inventory`.

## Next implementation slice

Phase 12 should implement a durable SQLite `InventoryStore` using the same application contracts, including restart tests for spool metadata, ledger idempotency and assignments. Only after durable persistence is proven should queue completion be connected to automatic inventory consumption.
