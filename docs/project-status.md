# FoxForge project status

**Snapshot date:** 2026-09-04  
**Canonical branch:** `main`  
**Main head at this snapshot:** `294ebc652504dc488a35740ff92c6c98ad20d0df`  
**Development version:** `0.1.0.dev0` (pre-alpha)

This document is a concise current-state snapshot. Detailed architecture remains normative in the ADRs and design specifications; `CHANGELOG.md` remains the implementation history.

## Current repository shape

ADR 0002 is now implemented in `main`:

```text
FoxForge/
├── backend/       Python 3.12+ core, adapters, fleet, queue, inventory and future API
├── deployment/    Docker/Umbrel packaging area
├── docs/          ADRs and durable design specifications
└── integrations/  isolated migration/provenance material
```

The `frontend/` top-level area is part of the target layout but is not yet in `main`; it currently exists in active PR #10.

## In `main`

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, normalized snapshots/events/errors, typed capability discovery and contract tests. |
| Printer adapters | Implemented foundation | `BambuAdapter` and `MoonrakerAdapter` coexist behind the same vendor-neutral contracts. |
| Fleet management | Implemented | `AdapterRegistry` and `FleetService` provide composition, lifecycle, snapshots, capabilities and merged normalized events. |
| Durable print queue | Implemented foundation | Restart-safe dispatch/idempotency, explicit `INDETERMINATE`, event-driven remote lifecycle tracking and SQLite persistence. |
| Queue retry runner | Implemented | Deterministic `QueueRunner.run_once()` with bounded exponential backoff for explicitly retryable pre-start failures only. |
| Bambu LAN transport | Implemented, hardware validation pending | MQTT/TLS, implicit FTPS, verified upload, double busy guards and fail-safe ambiguous-start handling. |
| Bambu project storage | Implemented seam | FTPS is the default strategy; future X2D/N6 internal-eMMC delivery remains hardware-led work behind `BambuProjectStorage`. |
| Moonraker transport | Implemented, hardware validation pending | HTTP/WebSocket transport, API-key auth, upload/start flow and normalized live state are covered by integration tests. |
| Filament/spool inventory | Phase 11 foundation implemented | Independent inventory bounded context, `Decimal` mass accounting, immutable idempotent adjustment ledger, physical slot assignments and `InMemoryInventoryStore`. |
| Repository layout | Implemented | Python project moved under `backend/`; deployment ownership split into Docker/Umbrel directories by ADR 0002. |
| Public API | Not implemented | REST/WebSocket/SSE boundary still needs to expose application services without leaking vendor transports. |
| Production deployment | Not implemented | Deployment directories exist, but production Docker/ARM64/Umbrel runtime packaging and smoke tests are still pending. |

## Inventory boundary after Phase 11

Inventory is now a real FoxForge domain instead of only a roadmap item.

Implemented:

- spool metadata and archive state;
- editable empty-spool mass;
- remaining/used filament derived from an immutable `Decimal` adjustment ledger;
- consumption, waste, return and correction adjustment kinds;
- idempotency keys and conflicting-replay detection;
- exactly-once replay semantics that remain valid after later archive;
- one-spool-per-physical-slot and one-slot-per-spool assignment rules;
- opaque `(printer_id, slot_id)` assignments without putting `spool_id` into printer adapter state.

Still required before automatic accounting is production-ready:

- durable SQLite inventory persistence;
- queue-completion consumption worker;
- material reservations before dispatch;
- 3MF/G-code estimate reconciliation;
- transaction/locking rules for future multi-process execution;
- public API DTOs and frontend integration.

## Active work not yet in `main`

### PR #10 — Web UI foundation

The React/TypeScript/Vite interface is implemented on `feature/web-ui-foundation` and its validation is green. It includes React Router, TanStack Query, i18next (`en`/`ru`/`uk`), responsive product views, printer cockpit, Queue, Materials, Farm, System and a restrained Ko-fi link.

It still uses a demo data gateway. The UI is not a live FoxForge client until the public backend API and realtime event transport exist.

PR #10 was based before both Phase 11 inventory and the ADR 0002 repository-layout merge. Before merge it should be updated onto current `main` so its README/docs changes preserve the inventory state and its `frontend/` directory lands cleanly alongside `backend/` and `deployment/`.

## Current safety/architecture invariants

The following rules should remain true as the project grows:

1. Common application/domain code must not import Bambu or Moonraker transport/protocol types.
2. Deep Bambu functionality stays available through typed Bambu capabilities rather than polluting common contracts.
3. Queue code never guesses whether an ambiguous print started; `INDETERMINATE` requires reconciliation and is never automatically retried.
4. Receipt-bearing jobs are never redispatched by retry logic.
5. Inventory owns FoxForge spool identity; printer material snapshots expose physical material state and opaque slot IDs, not `spool_id`.
6. Frontend code consumes public FoxForge application/API contracts, not Python modules or raw vendor payloads.
7. Docker and Umbrel must package the same application behavior rather than becoming divergent forks.
8. Upstream-derived code and behavior must retain required license/copyright provenance; newly written FoxForge code should remain clearly distinguishable.

## Recommended next sequence

1. **Update and merge PR #10** onto the current repository layout while preserving Phase 11 documentation and keeping its demo gateway explicitly non-production.
2. **Add durable SQLite inventory persistence** with restart tests and the same idempotency/assignment semantics as the in-memory store.
3. **Define the public REST + realtime API** over `FleetService`, `QueueService` and `InventoryService`, including explicit DTO/versioning and error semantics.
4. **Replace the frontend demo gateway** with the typed API client and realtime cache updates.
5. **Physically validate Bambu LAN/X2D and Moonraker/OpenKE transports** before claiming production printer support.
6. **Add queue scheduler/farm policy** above `QueueRunner.run_once()` with printer selection, priorities and durable multi-process lease/CAS semantics before distributed execution.
7. **Implement production Docker/ARM64/Umbrel packaging** only after the server API/runtime entrypoint is stable enough for end-to-end smoke tests.
8. **Expand deep Bambu capabilities** (AMS operations/drying, HMS, K profiles, dual nozzle, Virtual Printer) without weakening the vendor-independent core.

## Acceptance criteria for the next integration milestone

The next repository-level milestone should not be considered complete until:

- Python 3.12 and 3.13 backend CI remains green from `backend/`;
- all Phase 11 inventory tests continue to run from the new backend location;
- frontend typecheck, tests and production build are green after rebasing PR #10 onto current `main`;
- `README.md`, `docs/README.md`, ADR 0002 and this status document agree on the actual top-level layout;
- no merged documentation claims that the demo UI is live-connected to printers;
- no merged documentation claims physical Bambu/Moonraker validation before real hardware tests pass.
