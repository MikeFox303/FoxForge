# FoxForge project status

**Snapshot date:** 2026-09-04  
**Canonical branch:** `main`  
**Main head at this snapshot:** `5dca11b82424fd1e15fdcf34b18333e41315aa1f`  
**Development version:** `0.1.0.dev0` (pre-alpha)

This document is a concise current-state snapshot. Detailed architecture remains normative in the ADRs and design specifications; `CHANGELOG.md` remains the implementation history.

## Current repository shape

ADR 0002 is implemented in `main`:

```text
FoxForge/
├── backend/       Python 3.12+ core, adapters, fleet, queue, inventory and future API
├── frontend/      TypeScript/React/Vite web application
├── deployment/    Docker/Umbrel packaging area
├── docs/          ADRs and durable design specifications
└── integrations/  isolated migration/provenance material
```

Backend, frontend and deployment are independently testable ownership areas but remain parts of one FoxForge application.

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
| Web UI | Implemented foundation | React/TypeScript/Vite with React Router, TanStack Query, i18next (`en`/`ru`/`uk`), responsive fleet/queue/material/farm/system views, Spool Inventory and route-based printer cockpit. Still uses demo query gateways. |
| Repository layout | Implemented | Python project lives under `backend/`; frontend under `frontend/`; deployment ownership is split into Docker/Umbrel directories by ADR 0002. |
| Public API | Not implemented | REST/WebSocket/SSE boundary still needs to expose application services without leaking vendor transports. |
| Production deployment | Not implemented | Deployment directories exist, but production Docker/ARM64/Umbrel runtime packaging and smoke tests are still pending. |

## Inventory boundary after Phase 11

Inventory is a real FoxForge domain rather than only a roadmap item.

Implemented in the backend foundation:

- spool metadata and archive state;
- editable empty-spool mass;
- remaining/used filament derived from an immutable `Decimal` adjustment ledger;
- consumption, waste, return and correction adjustment kinds;
- idempotency keys and conflicting-replay detection;
- exactly-once replay semantics that remain valid after later archive;
- one-spool-per-physical-slot and one-slot-per-spool assignment rules;
- opaque `(printer_id, slot_id)` assignments without putting `spool_id` into printer adapter state.

The frontend now has a Spool Inventory workspace derived from those merged semantics. Its demo read model keeps Decimal masses as strings, treats physical slot IDs as opaque and resolves friendly slot labels against the normalized material-system snapshot instead of parsing vendor structure.

Still required before automatic accounting is production-ready:

- durable SQLite inventory persistence;
- queue-completion consumption worker;
- material reservations before dispatch;
- 3MF/G-code estimate reconciliation;
- transaction/locking rules for future multi-process execution;
- public Inventory API DTOs/mutations and replacement of the demo frontend gateway.

## Web UI boundary

The UI is now merged into `main`, but it is intentionally **not** presented as a live-connected production client yet.

Implemented:

- React Router product URLs for Overview, Printers, Queue, Materials, Inventory, Farm and System;
- `/printers/:printerId` route-based printer cockpit with Overview / Materials / Queue / Diagnostics tabs;
- mixed Bambu + Moonraker rendering from normalized frontend read models;
- TanStack Query data seams for fleet and inventory demo gateways;
- `en` / `ru` / `uk` localization infrastructure and growing page coverage;
- responsive dark FoxForge interface;
- restrained optional Ko-fi link in the sidebar footer;
- frontend CI for TypeScript, Vitest and production Vite build;
- documented main-driven parallel-development policy.

Not implemented yet:

- public REST client;
- WebSocket/SSE live cache updates;
- real printer/queue/inventory mutations;
- capability panels for deeper Bambu or Moonraker-specific controls that do not yet exist as merged typed capabilities.

Buttons for unavailable writes remain disabled rather than simulating durable application behavior.

## Parallel development rule

Frontend and backend may proceed concurrently, but `main` remains the only authoritative project state.

For UI work:

1. Start the UI branch from current `main`.
2. Open backend PRs may inform planning but are not stable frontend contracts.
3. Put server state behind TanStack Query gateways rather than page-local future endpoint assumptions.
4. Do not expose fake writes for commands whose API does not exist.
5. Mount vendor-specific controls only after corresponding typed capabilities are merged.
6. Immediately before merge, compare the UI branch with current `main`; if `main` advanced, update the branch and rerun the complete Web UI gate.
7. Recheck the post-merge `main` build.

The durable version of this rule is in `docs/design/frontend-parallel-development.md`.

## Current safety/architecture invariants

The following rules should remain true as the project grows:

1. Common application/domain code must not import Bambu or Moonraker transport/protocol types.
2. Deep Bambu functionality stays available through typed Bambu capabilities rather than polluting common contracts.
3. Queue code never guesses whether an ambiguous print started; `INDETERMINATE` requires reconciliation and is never automatically retried.
4. Receipt-bearing jobs are never redispatched by retry logic.
5. Inventory owns FoxForge spool identity; printer material snapshots expose physical material state and opaque slot IDs, not `spool_id`.
6. Frontend code consumes FoxForge application/API read models, not Python modules or raw vendor payloads.
7. Frontend preview data must not be mistaken for live printer state or durable writes.
8. Docker and Umbrel must package the same application behavior rather than becoming divergent forks.
9. Upstream-derived code and behavior must retain required license/copyright provenance; newly written FoxForge code should remain clearly distinguishable.

## Recommended next sequence

1. **Add durable SQLite inventory persistence** with restart tests and the same idempotency/assignment semantics as the in-memory store.
2. **Define the public REST + realtime API** over `FleetService`, `QueueService` and `InventoryService`, including explicit DTO/versioning and error semantics.
3. **Replace frontend demo gateways** with typed REST clients and feed WebSocket/SSE events into the TanStack Query cache.
4. **Add real UI mutations only as backend command endpoints land**, keeping missing actions disabled until then.
5. **Physically validate Bambu LAN/X2D and Moonraker/OpenKE transports** before claiming production printer support.
6. **Add queue scheduler/farm policy** above `QueueRunner.run_once()` with printer selection, priorities and durable multi-process lease/CAS semantics before distributed execution.
7. **Implement production Docker/ARM64/Umbrel packaging** after the server API/runtime entrypoint is stable enough for end-to-end smoke tests.
8. **Expand deep Bambu capabilities** (AMS operations/drying, HMS, K profiles, dual nozzle, Virtual Printer) without weakening the vendor-independent core; UI panels should follow those typed capabilities.

## Acceptance criteria for the next integration milestone

The next repository-level integration milestone should not be considered complete until:

- Python 3.12 and 3.13 backend CI remains green from `backend/`;
- Phase 11 inventory tests remain green after persistence/API work;
- frontend TypeScript, Vitest and production build remain green on current `main`;
- public API DTOs expose application contracts without leaking raw Bambu/Moonraker payloads;
- frontend live reads replace demo gateways through typed query clients rather than page rewrites;
- unavailable write actions remain disabled until matching command endpoints are tested;
- `README.md`, `docs/README.md`, ADR 0002 and this status document agree on the actual top-level layout and UI status;
- no merged documentation claims physical Bambu/Moonraker validation before real hardware tests pass.
