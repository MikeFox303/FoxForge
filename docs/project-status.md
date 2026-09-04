# FoxForge project status

**Snapshot date:** 2026-09-04  
**Canonical branch:** `main`  
**Implementation head reviewed before this documentation branch:** `9806b5416a35946ac56911eae8e992e4b5e68e69`  
**Published pre-release:** `v0.1.0-alpha.1` (`0.1.0a1` backend package)  
**Umbrel Community App:** `my3d-foxforge` in `MikeFox303/umbrel-3d-printing-store`  
**Maturity:** first public runnable/installable alpha; not production-ready

This document is the concise current-state snapshot for merged FoxForge work. ADRs and design specifications remain normative for architecture; `CHANGELOG.md` remains implementation history; `release/` contains durable release metadata/notes.

At this snapshot there are no open implementation pull requests. PR #32 (`feat(ui): surface inventory runtime state`) has merged; this status synchronization is documentation-only, and merged `main` remains the authoritative project and contract state.

## Release status

FoxForge `v0.1.0-alpha.1` is published as the first public pre-release.

The guarded release workflow:

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

Immutable multi-architecture digest used by the Umbrel package:

```text
sha256:f9bdb39893162df49e3a6eddfcdc10c3f950fbccaa4e3abb631711bd0605e54b
```

The release is for early testing and architecture validation, not production use. `main` has continued to receive UI/UX improvements after the `alpha.1` release; those changes require a later guarded release before they can be delivered by Docker/Umbrel without weakening immutable versioning.

## Current repository shape

ADR 0002 is implemented in `main`:

```text
FoxForge/
├── backend/       Python 3.12+ domain, adapters, services, API and runtime
├── frontend/      TypeScript/React/Vite web application
├── deployment/    Docker and Umbrel deployment contracts/documentation
├── docs/          ADRs, durable design specifications and status
└── integrations/  isolated migration/provenance material
```

Backend, frontend and deployment are independently testable ownership areas but compose into one FoxForge application. The actual Umbrel package definition lives in the companion Community App Store repository and reuses the same FoxForge release image.

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
| Alpha runtime | Implemented | `foxforge` composition root, versioned local printer config, offline-safe startup/reconnect, SPA + API from one `aiohttp` process. |
| Web UI | Live read integration implemented | React/TypeScript/Vite, TanStack Query, live `/api/v1` reads, explicit `?demo=1`, route-based printer cockpit and inventory workspace. Fleet and inventory loading/error/refresh/healthy-empty states are explicit in current `main`. |
| Localization | Alpha localization complete | English, Russian and Ukrainian (`en`, `ru`, `uk`) across shared workspaces and dynamic runtime states with parity tests. |
| Bambu LAN transport | Implemented, hardware validation pending | MQTT 3.1.1 over TLS, implicit FTPS, verified upload, double busy guards and fail-safe ambiguous-start behavior. |
| Bambu project storage | Implemented seam | FTPS default; future validated X2D/N6 internal-eMMC delivery remains behind `BambuProjectStorage`. |
| Moonraker transport | Implemented, hardware validation pending | HTTP/WebSocket, API-key auth, upload/start flow and normalized live state covered by integration tests. |
| Docker deployment | Runnable alpha implemented | Multi-stage unified image, standalone Compose, persistent `/data`, non-root steady state and startup smoke test in CI. |
| Release pipeline | First pre-release published | `v0.1.0-alpha.1` publishes a versioned multi-architecture GHCR image and GitHub pre-release. |
| ARM64 delivery | Published and CI runtime-smoked | Anonymous `linux/arm64` pull/start/health/UI/persistence validation passes under QEMU; representative Raspberry Pi 5 hardware validation remains pending. |
| Umbrel deployment | Alpha package implemented | `my3d-foxforge` merged in the Community Store, port `8283`, authenticated App Proxy, bridge networking, immutable release digest and persistent `/data`. |
| Command/write API | Not implemented | Printer control, queue mutations and inventory mutations remain intentionally unavailable over HTTP. |
| Realtime API | Not implemented | WebSocket/SSE delivery into the frontend cache remains future work. |
| Farm scheduler | Not implemented | Single-pass queue runner exists, but persistent scheduler/printer-selection policy and distributed leases are pending. |

## First runnable alpha runtime

PR #25 changed the project from separate backend/frontend foundations into a unified runnable application candidate. PR #28 prepared and published the first guarded public alpha pre-release. Subsequent UI PRs #29–#32 improved live runtime, empty-state and inventory error/refresh behavior in `main` without changing the released image retroactively.

Implemented behavior includes:

- `foxforge` executable server entrypoint;
- versioned local printer configuration for Bambu LAN and Moonraker adapters;
- safe empty `/data/config.json` creation on first start;
- web/API availability even when configured printers are offline;
- background printer reconnect attempts;
- queue and inventory persisted in the app-owned SQLite database;
- compiled React SPA and `/api/v1` served by the same `aiohttp` process;
- production frontend reads from real `/api/v1` fleet, queue and inventory endpoints;
- demo data retained only behind explicit `?demo=1`;
- unified multi-stage Docker image and standalone Compose stack;
- mounted data directory prepared before privilege drop, then non-root steady-state execution;
- CI smoke tests for `/healthz`, SPA and durable files;
- guarded versioned multi-architecture publication for Linux `amd64` and `arm64`.

Runtime safety boundaries remain explicit:

- vendor imports are restricted to the composition root rather than common domain/application code;
- no printer-control or inventory-mutation HTTP endpoints are exposed yet;
- no wildcard CORS or anonymous remote command API has been added;
- normal outbound bridge networking with explicit printer IPs is the alpha deployment model;
- printer network failures must not terminate the UI/API process;
- local credentials stay in `/data/config.json` and are not serialized by public read DTOs.

## Umbrel deployment status

The first FoxForge Community App package is merged in `MikeFox303/umbrel-3d-printing-store` through Store PR #20, squash commit `81323fbefca5c956f7052e6b4d967bfa60b4b9f8`.

Package contract:

```text
Store app ID:     my3d-foxforge
Umbrel app port:  8283
Internal server:  8000
Image:            ghcr.io/mikefox303/foxforge:0.1.0-alpha.1
Digest:           sha256:f9bdb39893162df49e3a6eddfcdc10c3f950fbccaa4e3abb631711bd0605e54b
Persistent data:  ${APP_DATA_DIR}/data -> /data
```

Security/deployment decisions:

- standard Umbrel App Proxy authentication remains enabled because FoxForge alpha has no app-level login yet;
- normal bridge networking is sufficient for explicit-IP Bambu LAN and Moonraker;
- no host networking, privileged mode, Docker socket or extra capabilities are granted;
- short/string bind volume syntax is used for umbrelOS 1.7.4 compatibility;
- `/healthz` is the runtime health check;
- `config.json` remains app-owned and mode `0600` on first-start validation.

Dedicated package validation passed for:

- package contract tests;
- `docker compose config` with an Umbrel App Proxy overlay;
- anonymous GHCR pull of the immutable release image on `linux/amd64`;
- anonymous GHCR pull of the immutable release image on `linux/arm64`;
- startup, `/healthz`, SPA and persistence smoke tests for both architectures;
- first-start `config.json` schema and SQLite creation;
- UID/GID `1000:1000` data ownership and `0600` config permissions.

The general Store Release Gate also remained green, including regression validation of the other packaged 3D-printing applications.

This makes the first alpha installable through the user-managed Umbrel Community App Store. It does not mean the app has been submitted to or accepted into Umbrel's official global App Store.

## Public API and frontend boundary

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

Inventory is durable rather than only an in-memory read model.

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
- live read DTOs consumed by the web UI;
- explicit inventory loading, error/retry, background-refresh and true-empty states so API failures are not presented as empty inventory.

Still required for automated accounting:

- material reservation before dispatch;
- trustworthy per-material print usage estimates;
- queue-completion consumption worker;
- 3MF/G-code estimate reconciliation and later actual-vs-estimated correction policy;
- authenticated inventory mutation API;
- stronger transaction/locking rules before multi-process execution.

## Web UI and localization

The merged UI provides:

- Overview, Printers, Queue, Materials, Inventory, Farm and System routes;
- `/printers/:printerId` cockpit with Overview / Materials / Queue / Diagnostics tabs;
- mixed Bambu + Moonraker rendering from normalized read models;
- live fleet, queue and inventory reads through typed `/api/v1` clients;
- explicit demo mode rather than silent production mock data;
- responsive dark interface;
- restrained optional Ko-fi link in the sidebar footer;
- persistent language selection;
- English, Russian and Ukrainian interface coverage;
- localization of dynamic printer, queue, material-source, runtime-state and relative-time states;
- translation parity tests;
- explicit fleet and inventory loading/error/retry/refresh/healthy-empty behavior;
- frontend CI for typechecking, Vitest and production Vite build.

PRs #29–#32 are merged in `main` and represent post-`alpha.1` UI improvements. They are not part of the immutable `alpha.1` image until a later versioned release is cut.

Deep vendor controls must continue to appear only after corresponding typed backend capabilities are merged. The UI must not invent unsupported Bambu or Moonraker controls.

## Upstream architecture strategy

ADR 0003 records the accepted roles of the upstream projects:

- **Bambuddy** is the primary Bambu protocol/behavior reference;
- **PrintBuddy** is the primary multi-vendor/provider-isolation reference;
- **PrintOps** is the primary operations/farm/scheduling reference;
- **FoxForge** retains ownership of the common domain, capability model, events, durable queue, inventory, API/frontend contracts and deployment behavior.

This strategy is not a wholesale merge or fork. Upstream ideas are translated through FoxForge boundaries, and any copied/derived material must retain traceable provenance and required notices.

## Hardware validation boundary

The largest remaining technical uncertainty is real hardware behavior rather than core architecture or packaging.

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

Umbrel/Raspberry Pi validation still needs real-device evidence for:

- installation/restart on representative Raspberry Pi 5 hardware;
- Bambu X2D reachability from the actual Umbrel network environment;
- Ender/OpenKE/Moonraker reachability from the actual Umbrel network environment;
- persistence and upgrade behavior across later FoxForge package versions.

Documentation must not call these transports or the full deployment production-validated until physical tests pass.

## Current architecture and safety invariants

1. Common application/domain code must not import Bambu or Moonraker transport/protocol types.
2. Deep Bambu functionality remains available through typed Bambu capabilities rather than polluting common contracts.
3. Queue code never guesses whether an ambiguous print started; `INDETERMINATE` requires reconciliation and is never automatically retried.
4. Receipt-bearing jobs are never redispatched by retry logic.
5. Inventory owns FoxForge spool identity; printer material snapshots expose physical material state and opaque slot IDs, not `spool_id`.
6. Public API DTOs expose FoxForge application contracts rather than raw vendor payloads or local secrets.
7. Frontend code consumes typed FoxForge API/read models rather than Python modules or vendor protocol structures.
8. Missing write APIs remain visibly unavailable instead of simulated as durable operations.
9. Docker and Umbrel package the same FoxForge application behavior rather than becoming divergent forks.
10. Umbrel App Proxy authentication remains enabled while FoxForge lacks a defined application-authentication contract.
11. Upstream-derived code/material must retain required license/copyright provenance; newly written FoxForge code remains clearly distinguishable.
12. Bambuddy, PrintBuddy and PrintOps are specialized references, not FoxForge's base framework; architectural translation happens through FoxForge contracts.
13. Scheduler/farm logic must depend on FoxForge capabilities and persisted application state, never directly on vendor transports.

## Recommended next sequence

1. **Physical alpha validation:** run Bambu LAN/X2D and Moonraker/OpenKE through connect → state → upload → print start → lifecycle → completion matrices and document results.
2. **Representative Umbrel validation:** install `my3d-foxforge` on Raspberry Pi 5/UmbrelOS, confirm restart/persistence and verify explicit-IP reachability to both real printer families.
3. **Next guarded alpha release:** package the merged post-`alpha.1` UI/UX improvements only after all release gates pass; update the Store to the new immutable digest rather than using a floating tag.
4. **Command API security contract:** define authentication/authorization, request validation, idempotency keys, normalized errors and audit expectations before adding remote writes.
5. **Queue/printer/inventory mutations:** add narrowly scoped tested command endpoints and enable matching UI actions only after contracts exist.
6. **Realtime updates:** add WebSocket/SSE application events and update TanStack Query caches without leaking vendor transports.
7. **Automatic filament accounting:** reservations, per-material estimates, queue-completion consumption and reconciliation.
8. **Farm scheduler:** persistent scheduling, printer selection, priorities/deadlines and durable lease/CAS semantics before distributed runners; use PrintOps as an operations reference without weakening FoxForge queue safety.
9. **Deep Bambu expansion:** AMS operations/drying, HMS, K profiles, dual nozzle and Virtual Printer/X2D-specific capabilities behind typed Bambu interfaces; use Bambuddy as the primary behavior reference.
10. **Additional vendors:** only after common contracts have been exercised by the first two real adapter families on hardware; use the PrintBuddy/provider pattern only as structural guidance.

## Acceptance criteria for the next major milestone

The next major alpha milestone should not be considered complete until:

- backend CI remains green on Python 3.12 and 3.13;
- frontend typecheck, tests and production build remain green;
- unified container startup smoke tests remain green;
- Umbrel package contract and anonymous amd64/arm64 runtime tests remain green;
- at least one real Bambu target and one real Moonraker/OpenKE target complete documented connectivity/state validation;
- representative Raspberry Pi 5/Umbrel installation, restart and persistence are documented;
- any new write endpoint has authentication/authorization assumptions, request validation, idempotency and error-contract tests;
- API/application layers still contain no vendor transport imports;
- `INDETERMINATE` and receipt-bearing queue safety semantics are preserved;
- inventory Decimal/idempotency/restart guarantees remain intact;
- architecture-significant work follows ADR 0003's upstream role/provenance rules;
- README, project status and deployment docs agree on what is live, what is read-only, what is released and what is physically validated;
- no documentation claims production-ready hardware support before the corresponding physical test evidence exists.
