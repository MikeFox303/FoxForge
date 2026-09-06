# SQLite inventory persistence

- **Status:** implemented durable store
- **Updated:** 2026-09-06
- **Related:** [inventory foundation](inventory-foundation.md), [inventory atomicity](inventory-atomicity.md)

## Purpose

`SQLiteInventoryStore` provides restart-safe persistence for FoxForge spool metadata, append-only mass history and inventory-owned physical slot assignments without leaking SQLite details into domain/application/UI contracts.

## Storage model

SQLite owns the inventory persistence tables for:

- current spool metadata;
- append-only adjustments with durable idempotency identity;
- current spool-to-physical-slot assignments.

Database constraints preserve spool/adjustment identity and one-to-one assignment uniqueness. Foreign keys, WAL mode and a bounded busy timeout support the current single-process/container deployment model.

## Serialization

Persisted payloads are versioned. `Decimal` mass values are stored as decimal strings, and dates/timestamps round-trip through domain constructors so validation remains active on read.

Unsupported payload/schema versions fail closed rather than being guessed.

## Idempotency and atomicity

Semantic adjustment idempotency remains an application rule, with SQLite uniqueness as a durable backstop.

Current implementation also keeps balance validation, idempotency checks and adjustment insertion inside the required atomic persistence boundary. Concurrency/restart tests protect against duplicate deduction and invalid balance races.

## Restart guarantees

Durable tests cover:

- spool metadata and editable empty-spool mass;
- exact ledger/balance reconstruction;
- idempotent adjustment replay after restart;
- archived-spool replay safety;
- physical assignments and slot uniqueness;
- explicit unassign/move behavior.

## Boundary

Frontend/API clients never read SQLite directly. They consume `InventoryService` DTOs. Inventory persistence imports no vendor printer packages, and printer material snapshots remain free of FoxForge `spool_id`.

## Current scope

Implemented:

- durable operator inventory workflow;
- atomic/idempotent adjustments;
- restart-safe assignments/history;
- migration/version ownership through the shared persistence layer.

Not implemented as a released feature:

- automatic queue/job filament consumption;
- material reservation/consumption P3 workflow;
- distributed multi-process inventory writers.

## Acceptance criteria

- exact Decimal values survive round trip/restart;
- idempotency survives restart and concurrency;
- assignment uniqueness survives restart;
- persistence details do not leak into domain/API contracts;
- vendor adapters do not become inventory dependencies;
- P3 automatic accounting remains separate from the normal durable inventory store.
