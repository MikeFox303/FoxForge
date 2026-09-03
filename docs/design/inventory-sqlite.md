# SQLite inventory persistence

Status: Phase 12 design specification

Related: ADR 0001, ADR 0002, `docs/design/inventory-foundation.md`

## Context

Phase 11 established FoxForge-owned spool metadata, an immutable mass-adjustment ledger and inventory-owned physical slot assignments behind `InventoryStore`. The next requirement is durable single-container persistence suitable for Docker, ARM64 and Umbrel without leaking database details into the inventory domain or the parallel frontend.

FoxForge already uses SQLite successfully for durable print-queue state. Inventory follows the same deployment direction while retaining a separate store boundary and schema.

## Decision

Implement `SQLiteInventoryStore` under `backend/src/foxforge/infrastructure/inventory/`.

The store implements the existing `InventoryStore` protocol; `InventoryService`, `domain.inventory`, printer adapters and frontend code remain unchanged.

## Storage model

SQLite owns three tables:

- `inventory_spools` — current spool metadata as a versioned JSON payload;
- `inventory_adjustments` — append-only ledger records with a database-level unique `idempotency_key`;
- `inventory_assignments` — current one-spool/one-physical-slot mapping.

Database constraints enforce:

- unique spool IDs;
- unique adjustment IDs;
- unique adjustment idempotency keys;
- adjustment foreign keys to existing spools;
- one assignment per spool;
- one assignment per `(printer_id, slot_id)` pair.

The store enables SQLite foreign keys, WAL mode and a five-second busy timeout for the current single-container deployment model.

## Serialization

Each persisted domain object carries `schema_version = 1` in its JSON payload.

`Decimal` filament masses are serialized as decimal strings rather than JSON floating-point numbers. Dates and timezone-aware datetimes use ISO 8601 values and are reconstructed through the existing domain constructors, so domain validation still runs on read.

Explicit schema-version checking fails closed on unsupported payload versions instead of silently interpreting incompatible records.

## Idempotency and restart safety

The application service remains responsible for semantic idempotency: identical adjustment replay returns the existing record and materially different reuse raises `InventoryIdempotencyConflictError`.

SQLite additionally enforces uniqueness of `idempotency_key` below the service layer. This protects the persistence boundary against accidental duplicate writes and establishes the durable prerequisite for future queue-driven exactly-once consumption.

Restart tests must prove that:

- spool metadata survives process/store recreation;
- ledger balance is identical after restart;
- adjustment idempotency survives restart;
- a recorded adjustment remains replayable after the spool is later archived;
- assignments survive restart;
- slot uniqueness survives restart and explicit unassign/move operations.

## Backend/frontend boundary

Phase 12 changes only `backend/**`, this design document and the project changelog. It does not modify `frontend/**`, root `README.md` or `docs/README.md`, which avoids conflicts with the parallel web-interface PR.

The frontend must not read SQLite directly. A later public API will expose application read models from `InventoryService`; persistence layout and JSON payload schema remain backend implementation details.

## Concurrency boundary

This phase targets FoxForge's current one-process/one-container runtime. WAL and SQLite uniqueness constraints provide durable local consistency, but Phase 12 does not claim distributed transaction or multi-process scheduling support.

Before multiple backend writers are introduced, inventory writes that combine balance validation and append operations will require an explicit transactional/CAS design.

## Out of scope

- HTTP/REST inventory endpoints;
- WebSocket/SSE inventory events;
- automatic queue-completion deduction;
- reservation of material before dispatch;
- material-use extraction from 3MF/G-code;
- RFID/tag-to-spool matching;
- distributed/multi-process write coordination;
- frontend changes.

## Acceptance criteria

- `SQLiteInventoryStore` implements the existing `InventoryStore` contract without changing domain models;
- inventory infrastructure imports no printer or vendor packages;
- `Decimal` mass values round-trip exactly;
- spool metadata, empty-spool weight and archive state survive restart;
- adjustment ledger and computed balance survive restart;
- database-level idempotency-key uniqueness is enforced;
- identical adjustment replay remains exactly-once after restart and later archive;
- physical slot assignments and uniqueness survive restart;
- WAL, foreign keys and busy timeout are enabled;
- no frontend files are modified;
- Ruff, formatting and full pytest suite pass on Python 3.12 and 3.13.

## Next implementation direction

After durable inventory persistence is merged, the next backend slice should define a stable public application/API read boundary for fleet, queue and inventory so the parallel web UI can replace its mock gateway without importing backend internals. Automatic consumption should follow only after FoxForge has a trustworthy per-material usage estimate source and a durable queue-to-inventory accounting identity.
