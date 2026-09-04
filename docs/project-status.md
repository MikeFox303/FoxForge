# FoxForge project status

**Snapshot date:** 2026-09-04  
**Canonical branch:** `main`  
**Implementation head reviewed:** `d5b69835f04751b47ba710cccf59a26e6d0734c9`  
**Published pre-release:** `v0.1.0-alpha.1` (`0.1.0a1` backend package)  
**Maturity:** first public runnable alpha pre-release; not production-ready

This document is the concise current-state snapshot for merged FoxForge work. ADRs and design specifications remain normative for architecture; `CHANGELOG.md` remains the implementation history; `release/` contains durable release metadata/notes.

At this snapshot, PR #29 (`feat(ui): surface live API runtime state`) is open against `main`. Architecture and implementation work may continue in parallel, but merged `main` remains the authoritative contract state.

## Release status

FoxForge `v0.1.0-alpha.1` is published as the first public pre-release.

The release workflow now:

- validates release manifest/version consistency;
- runs backend lint/format/tests;
- runs frontend typecheck/tests/build;
- builds and smoke-tests the unified application image;
- publishes a versioned GHCR image for Linux `amd64` and `arm64`;
- creates the GitHub tag/pre-release only after guarded validation succeeds.

Published image:

```text
ghcr.io/mikefox303/foxforge:0.1.0-alpha.1
```

The multi-architecture image is published, but representative ARM64 device runtime validation remains pending. The pre-release is for early testing and architecture validation, not production use.

## Current repository shape

ADR 0002 is implemented in `main`:

```text
FoxForge/
├── backend/       Python 3.12+ domain, adapters, services, API and runtime
├── frontend/      TypeScript/React/Vite web application
├── deployment/    Docker runtime and future Umbrel packaging
├── docs/          ADRs, durable design specifications and status
└── integrations/  isolated migration/provenance material
```

Backend, frontend and deployment are independently testable ownership areas but now compose into one runnable FoxForge application.

## Current `main` status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, normalized snapshots/events/errors, typed capability discovery and contract tests. |
| Printer adapters | Implemented foundation | `BambuAdapter` and `MoonrakerAdapter` coexist behind vendor-neutral contracts. |
| Fleet management | Implemented | `AdapterRegistry` and `FleetService` provide composition, lifecycle, snapshots, capabilities and merged normalized events. |
| Durable print queue | Implemented foundation | SQLite-backed dispatch/idempotency, explicit `INDETERMINATE`, remote lifecycle tracking and terminal persistence. |
| Queue retry runner | Implemented | Deterministic `QueueRunner.run_once()` with bounded exponential backoff only for explicitly retryable pre-start failures. |
| Filament/spool inventory | Durable foundation implemented | Independent bounded context, exact `Decimal` mass ledger, idempotent adjustments, slot assignments and SQLite restart durability. |
| Public HTTP API v1 | Implemented read-only | `/healthz`, `/api/v1/fleet`, `/api/v1/queue`, `/api/v1/inventory/spools`; normalized DTOs, no raw vendor payloads or secret leakage. |
| Alpha runtime | Implemented | `foxforge` server composition root, versioned local printer config, offline-safe startup/reconnect, SPA + API from one `aiohttp` process. |
| Web UI | Live read integration implemented | React/TypeScript/Vite, TanStack Query, live `/api/v1` reads, explicit `?demo=1` preview mode, route-based printer cockpit and inventory workspace. |
| Localization | Alpha localization complete | English, Russian and Ukrainian (`en`, `ru`, `uk`) across shared workspaces and dynamic runtime states with parity tests. |
| Bambu LAN transport | Implemented, hardware validation pending | MQTT 3.1.1 over TLS, implicit FTPS, verified upload, double busy guards and fail-safe ambiguous-start behavior. |
| Bambu project storage | Implemented seam | FTPS default; future validated X2D/N6 internal-eMMC delivery remains behind `BambuProjectStorage`. |
| Moonraker transport | Implemented, hardware validation pending | HTTP/WebSocket, API-key auth, upload/start flow and normalized live state covered by integration tests. |
| Docker deployment | Runnable alpha implemented | Multi-stage unified image, standalone Compose, persistent `/data`, non-root steady state and startup smoke test in CI. |
| Release pipeline | First pre-release published | `v0.1.0-alpha.1` guarded workflow publishes a versioned multi-architecture GHCR image and GitHub pre-release. |
| ARM64 delivery | Published, runtime validation pending | Release image targets Linux `amd64` + `arm64`; representative ARM64 execution still needs validation. |
| Umbrel deployment | Not implemented yet | Packaging boundary exists and must reuse the same FoxForge runtime/image contract. |
| Command/write API | Not implemented | Printer control, queue mutations and inventory mutations remain intentionally unavailable over HTTP. |
| Realtime API | Not implemented | WebSocket/SSE delivery into the frontend cache remains future work. |
| Farm scheduler | Not implemented | Single-pass queue runner exists, but persistent scheduler/printer-selection policy and distributed leases are pending. |

## First runnable alpha runtime

PR #25 changed the project from separate backend/frontend foundations into a unified runnable application candidate. PR #28 then prepared and published the first guarded public alpha pre-release.

Implemented behavior:

- `foxforge` executable server entrypoint;
- versioned local printer configuration for Bambu LAN and Moonraker adapters;
- safe empty `/data/config.json` creation on first start;
- web/API availability even when configured printers are offline;
- background printer reconnect attempts;
- queue and inventory persisted in the app-owned SQLite database;
- compiled React SPA and `/api/v1` served by the same `aiohttp` process;
- production frontend reads from the real `/api/v1` fleet, queue and inventory endpoints;
- demo data retained only behind explicit `?demo=1`;
- unified multi-stage Docker image and standalone Compose stack;
- mounted data directory prepared before privilege drop, then non-root steady-state execution;
- CI smoke test that starts the image and checks `/healthz`, the SPA and durable files;
- guarded versioned multi-architecture publication for Linux `amd64` and `arm64`.

Runtime safety boundaries remain explicit:

- vendor imports are restricted to the composition root rather than common domain/application code;
- no printer-control or inventory-mutation HTTP endpoints are exposed yet;
- no wildcard CORS or anonymous remote command API has been added;
- normal outbound bridge networking with explicit printer IPs is the alpha deployment model; `network_mode: host` is not required by design;
- printer network failures must not terminate the UI/API process;
- local credentials stay in `/data/config.json` and are not serialized by public read DTOs.

## Public API and frontend boundary

The production UI is no longer a mock-only client.

Current read path:

```text
printer adapters / inventory / queue
              |
        application services
              |
          /api/v1 DTOs
              |
       typed frontend client
              |
        TanStack Query
              |
          React views
```

Implemented read endpoints:

- `GET /healthz`;
- `GET /api/v1/fleet`;
- `GET /api/v1/queue`;
- `GET /api/v1/inventory/spools`.

The API uses normalized vendor-independent DTOs, exact decimal strings for inventory mass, safe queue artifact metadata and version/cache headers. The frontend consumes these read models in normal runtime mode.

Still intentionally absent:

- printer command endpoints;
- queue enqueue/retry/reconcile/cancel mutations;
- inventory create/move/correct/archive mutations;
- remote printer credential/configuration writes;
- WebSocket/SSE realtime delivery;
- authentication/authorization claims for command APIs.

Unavailable UI writes must remain disabled until corresponding backend commands have explicit authentication, validation, idempotency and normalized HTTP error semantics.

## Inventory status

Inventory is now durable, not just an in-memory Phase 11 model.

Implemented:

- spool metadata and archive state;
- editable empty-spool mass;
- exact `Decimal` serialization;
- immutable adjustment ledger for consumption, waste, return and correction;
- idempotency keys and conflicting-replay rejection;
- exactly-once replay behavior across restart and after later archive;
- one spool per physical `(printer_id, slot_id)` and one slot per spool;
- opaque physical slot IDs without `spool_id` pollution in printer snapshots;
- SQLite WAL, foreign keys and busy timeout for the current single-container runtime;
- restart tests for metadata, ledger balance, archive replay and assignments;
- live read DTOs consumed by the web UI.

Still required for automated accounting:

- material reservation before dispatch;
- trustworthy per-material print usage estimates;
- queue-completion consumption worker;
- 3MF/G-code estimate reconciliation and later actual-vs-estimated correction policy;
- authenticated inventory mutation API;
- stronger transaction/locking rules before multi-process execution.

## Web UI and localization

The merged UI currently provides:

- Overview, Printers, Queue, Materials, Inventory, Farm and System routes;
- `/printers/:printerId` cockpit with Overview / Materials / Queue / Diagnostics tabs;
- mixed Bambu + Moonraker rendering from normalized read models;
- live fleet, queue and inventory reads through typed `/api/v1` clients;
- explicit demo mode rather than silent production mock data;
- responsive dark interface;
- restrained optional Ko-fi link in the sidebar footer;
- persistent language selection;
- English, Russian and Ukrainian interface coverage;
- localization of dynamic printer, queue, material-source and relative-time states;
- translation parity tests to prevent missing alpha keys;
- frontend CI for typechecking, Vitest and production Vite build.

PR #29 is improving the first-run/degraded-server presentation so the UI distinguishes connecting, ready, refreshing and API-failure states without inventing backend capabilities.

Deep vendor controls must continue to appear only after corresponding typed backend capabilities are merged. The UI should not invent unsupported Bambu or Moonraker controls.

## Upstream architecture strategy

ADR 0003 records the accepted roles of the upstream projects:

- **Bambuddy** is the primary Bambu protocol/behavior reference;
- **PrintBuddy** is the primary multi-vendor/provider-isolation reference;
- **PrintOps** is the primary operations/farm/scheduling reference;
- **FoxForge** retains ownership of the common domain, capability model, events, durable queue, inventory, API/frontend contracts and deployment behavior.

This strategy is intentionally not a wholesale merge or fork. Upstream ideas are translated through FoxForge boundaries, and any copied/derived material must retain traceable provenance and required notices.

## Hardware validation boundary

The largest remaining technical uncertainty is now real hardware behavior rather than core architecture.

Bambu validation still needs real-device evidence for:

- connection/reconnect against the target LAN-mode printer;
- state synchronization;
- FTPS project delivery;
- print-start acknowledgement and ambiguous-start behavior;
- lifecycle completion matching;
- X2D/N6 storage behavior, especially any internal-eMMC path;
- later AMS/drying/HMS/dual-nozzle capabilities.

Moonraker/OpenKE validation still needs real-device evidence for:

- API-key/auth configuration where applicable;
- HTTP/WebSocket connection and reconnect;
- live state subscriptions;
- G-code upload/checksum/start;
- print lifecycle completion and failure handling.

Documentation must not call these transports production-validated until physical tests pass.

## Deployment status

The Docker boundary has moved from placeholder to published runnable alpha:

- unified backend + compiled frontend image;
- standalone `docker-compose.yml`;
- external persistent data directory;
- safe first-start config/database creation;
- non-root application execution after volume preparation;
- health/startup smoke testing in CI;
- guarded Linux `amd64` + `arm64` publication workflow;
- first versioned image published as `ghcr.io/mikefox303/foxforge:0.1.0-alpha.1`.

Still required before a production-grade deployment release:

- representative ARM64 runtime smoke test on target hardware;
- upgrade/migration policy for persisted state;
- user-facing configuration documentation;
- Umbrel App Store manifest/icon/gallery/runtime integration;
- Umbrel end-to-end ARM64 smoke test using the same application image/behavior;
- later stable-channel/digest/upgrade policy beyond the initial alpha release path.

## Current architecture and safety invariants

1. Common application/domain code must not import Bambu or Moonraker transport/protocol types.
2. Deep Bambu functionality remains available through typed Bambu capabilities rather than polluting common contracts.
3. Queue code never guesses whether an ambiguous print started; `INDETERMINATE` requires reconciliation and is never automatically retried.
4. Receipt-bearing jobs are never redispatched by retry logic.
5. Inventory owns FoxForge spool identity; printer material snapshots expose physical material state and opaque slot IDs, not `spool_id`.
6. Public API DTOs expose FoxForge application contracts rather than raw vendor payloads or local secrets.
7. Frontend code consumes typed FoxForge API/read models rather than Python modules or vendor protocol structures.
8. Missing write APIs remain visibly unavailable instead of simulated as durable operations.
9. Docker and Umbrel must package the same FoxForge application behavior rather than becoming divergent forks.
10. Upstream-derived code/material must retain required license/copyright provenance; newly written FoxForge code remains clearly distinguishable.
11. Bambuddy, PrintBuddy and PrintOps are specialized references, not FoxForge's base framework; architectural translation happens through FoxForge contracts.
12. Scheduler/farm logic must depend on FoxForge capabilities and persisted application state, never directly on vendor transports.

## Recommended next sequence

1. **Physical alpha validation:** run Bambu LAN/X2D and Moonraker/OpenKE through connect → state → upload → print start → lifecycle → completion test matrices and document results.
2. **Command API security contract:** define authentication/authorization, request validation, idempotency keys, normalized errors and audit expectations before adding remote writes.
3. **Queue/printer/inventory mutations:** add narrowly scoped tested command endpoints and enable matching UI actions only after contracts exist.
4. **Realtime updates:** add WebSocket/SSE application events and update TanStack Query caches without leaking vendor transports.
5. **Automatic filament accounting:** reservations, per-material estimates, queue-completion consumption and reconciliation.
6. **Farm scheduler:** persistent scheduling, printer selection, priorities/deadlines and durable lease/CAS semantics before distributed runners; use PrintOps as an operations reference without weakening FoxForge queue safety.
7. **Deep Bambu expansion:** AMS operations/drying, HMS, K profiles, dual nozzle and Virtual Printer/X2D-specific capabilities behind typed Bambu interfaces; use Bambuddy as the primary behavior reference.
8. **Release deployment:** validate ARM64, define upgrades and build the Umbrel package around the same runtime.
9. **Additional vendors:** only after common contracts have been exercised by the first two real adapter families on hardware; use the PrintBuddy/provider pattern only as structural guidance.

## Acceptance criteria for the next major milestone

The next major alpha milestone should not be considered complete until:

- backend CI remains green on Python 3.12 and 3.13;
- frontend typecheck, tests and production build remain green;
- unified container startup smoke tests remain green;
- at least one real Bambu target and one real Moonraker/OpenKE target complete documented connectivity/state validation;
- any new write endpoint has authentication/authorization assumptions, request validation, idempotency and error-contract tests;
- API/application layers still contain no vendor transport imports;
- `INDETERMINATE` and receipt-bearing queue safety semantics are preserved;
- inventory Decimal/idempotency/restart guarantees remain intact;
- architecture-significant work follows ADR 0003's upstream role/provenance rules;
- README, project status and deployment docs agree on what is live, what is read-only, what is released and what is physically validated;
- no documentation claims production-ready hardware support before the corresponding physical test evidence exists.
