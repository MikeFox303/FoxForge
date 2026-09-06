# Inventory foundation

- **Status:** durable implementation and normal operator workflow released
- **Updated:** 2026-09-06
- **Related:** [SQLite inventory](inventory-sqlite.md), [inventory atomicity](inventory-atomicity.md), [printer contracts](printer-contracts.md)

## Purpose

FoxForge inventory is an independent bounded context for spool identity and mass accounting across mixed printer fleets. Printer material snapshots describe physical sources; they do not contain FoxForge `spool_id` values.

## Spool model

A `Spool` owns:

- stable spool ID;
- material/manufacturer/product/color metadata;
- initial and remaining filament mass;
- optional editable empty-spool mass;
- optional purchase date;
- archive state and timestamps.

Mass uses `Decimal`, never binary floating point as authoritative storage/accounting.

## Immutable mass ledger

Remaining filament derives from initial mass plus append-only adjustments. Adjustment kinds include consumption, waste, return and correction.

A stored adjustment is immutable; corrections append history. Balance validation prevents remaining filament from becoming negative or exceeding the original filament mass.

Adjustment idempotency is durable and atomic with the balance check/mutation. Same-key/same-request replay returns the original logical adjustment; changed payload under the same key conflicts.

## Physical assignments

Inventory owns the association:

```text
spool_id <-> (printer_id, opaque slot_id)
```

Rules:

- one spool at most one physical slot;
- one physical slot at most one FoxForge spool;
- same spool/same slot assignment is idempotent;
- moving requires explicit unassign;
- archived spools cannot receive new assignments;
- assigned spools must be unassigned before archive.

`slot_id` is opaque. Inventory does not parse AMS, CFS, tray or Moonraker topology.

## Persistence

The original in-memory contract implementation has been followed by a durable SQLite store with restart/idempotency coverage. Persistence details remain behind `InventoryStore`; application/domain contracts do not depend on SQLite rows.

## Current operator workflow

Implemented read/write workflows include:

- create spool;
- edit empty-spool mass;
- correct mass;
- assign / move / unassign;
- archive;
- inspect history.

The web/API layer derives DTOs from `InventoryService`; React types and persistence rows are not authoritative domain definitions.

## Automatic accounting boundary

Automatic queue/job filament consumption is **not** part of the current released inventory workflow. P3 remains frozen behind physical/deployment validation.

When resumed, automatic accounting must preserve:

- deterministic exactly-once idempotency from durable job/queue identity;
- exact Decimal mass handling;
- explicit material plan/binding semantics;
- restart/replay safety;
- inventory ownership of spool identity rather than inserting `spool_id` into printer snapshots.

## Acceptance criteria

- inventory domain remains independent from vendor adapters/transports;
- no `spool_id` enters `MaterialSystemCapability` snapshots;
- exact mass and adjustment history survive restart;
- adjustment mutation is atomic/idempotent;
- balances stay within valid range;
- assignment uniqueness and explicit move/unassign rules hold;
- archived-spool rules hold;
- UI/API keep `slotId` opaque;
- automatic accounting is not implied by the normal operator workflow.
