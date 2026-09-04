# FoxForge project status

**Snapshot date:** 2026-09-04  
**Canonical branch:** `main`  
**Published pre-release:** `v0.1.0-alpha.2` (`0.1.0a2` backend package)  
**Umbrel Community App:** `my3d-foxforge` in `MikeFox303/umbrel-3d-printing-store`  
**Maturity:** runnable/installable alpha; not production-ready

This document is the concise current-state snapshot for FoxForge. ADRs and design specifications remain normative for architecture; `CHANGELOG.md` remains implementation history; `release/` contains durable release metadata and notes.

The published `alpha.2` image is immutable. Features described below as post-`alpha.2` are present in repository `main` only after their merge and require a later guarded release before Docker/Umbrel users receive them.

## Release status

FoxForge `v0.1.0-alpha.2` is the current published pre-release.

The guarded release workflow validates release/version consistency, backend and frontend gates, the unified container, and multi-architecture image publication before creating the GitHub pre-release. The release remains for early testing and architecture validation, not production use.

## Current repository shape

ADR 0002 is implemented:

```text
FoxForge/
├── backend/       Python 3.12+ domain, adapters, services, API and runtime
├── frontend/      TypeScript/React/Vite web application
├── deployment/    Docker and Umbrel deployment contracts/documentation
├── docs/          ADRs, durable design specifications and status
└── integrations/  isolated migration/provenance material
```

Backend, frontend and deployment are independently testable ownership areas but compose into one FoxForge application. The Umbrel package definition lives in the companion Community App Store repository and reuses the same FoxForge release image.

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, normalized snapshots/events/errors, typed capability discovery and contract tests. |
| Printer adapters | Implemented foundation | `BambuAdapter` and `MoonrakerAdapter` coexist behind vendor-neutral contracts. |
| Fleet management | Implemented | `AdapterRegistry` and `FleetService` provide dynamic composition, lifecycle, snapshots, capabilities and normalized events. |
| Durable print queue | Implemented foundation | SQLite-backed dispatch/idempotency, explicit `INDETERMINATE`, remote lifecycle tracking and terminal persistence. |
| Queue retry runner | Implemented | Deterministic bounded pre-start retry policy; uncertain or receipt-bearing jobs are never blindly retried. |
| Filament/spool inventory | Durable foundation implemented | Exact `Decimal` ledger, idempotent adjustments, physical assignments, archive semantics and SQLite restart durability. |
| Public HTTP API v1 reads | Implemented | `/healthz`, fleet, queue and inventory read models; no raw vendor payloads or filesystem paths. |
| Command API security | Implemented foundation | Fail-closed bearer/trusted-browser sessions, principals/permissions, request IDs, normalized errors and durable idempotency. |
| Printer configuration writes | Implemented post-alpha.2 | Authenticated add/update/remove/test/reconnect flows; credentials remain outside public read DTOs. |
| Inventory writes | Implemented post-alpha.2 | Authenticated/idempotent create/correct/empty-mass/move/unassign/archive commands. |
| Queue write API | Implemented post-alpha.2 | Safe content-addressed artifact staging plus authenticated/idempotent enqueue, dispatch and explicit reconciliation; no client filesystem paths and no blind retry endpoint. |
| Command audit | Implemented post-alpha.2 | Append-only SQLite audit for printer/inventory/queue command routes with non-secret idempotency digests. |
| Alpha runtime | Implemented | Single `aiohttp` server, offline-safe printer composition, reconnect supervision, SPA + API and persistent `/data`. |
| Web UI | Live read integration implemented | React/TypeScript/Vite, TanStack Query, route-based printer cockpit and inventory workspace. Some guarded write flows are enabled where browser command sessions exist; queue upload/dispatch UI remains the next integration step. |
| Localization | Alpha localization complete | English, Russian and Ukrainian across shared workspaces and dynamic runtime states. |
| Bambu LAN transport | Implemented, hardware validation pending | MQTT/TLS, project delivery, verified upload, busy guards and fail-safe ambiguous-start handling. |
| Moonraker transport | Implemented, hardware validation pending | HTTP/WebSocket, API-key auth, upload/start flow and normalized live state covered by automated tests. |
| Docker deployment | Runnable alpha implemented | Unified multi-stage image, persistent `/data`, non-root steady-state execution and startup smoke testing. |
| ARM64 delivery | Published and CI runtime-smoked | Multi-architecture release images; representative Raspberry Pi 5 hardware validation remains pending. |
| Umbrel deployment | Alpha package implemented | Authenticated App Proxy, bridge networking, immutable release digest and persistent `/data`. |
| Realtime API | Not implemented | WebSocket/SSE application-event delivery into frontend query caches remains future work. |
| Farm scheduler | Not implemented | Queue runner exists, but persistent scheduling/printer selection/deadlines/leases are pending. |

## Queue command and artifact boundary

The post-`alpha.2` queue command API follows this path:

```text
client file bytes
      |
POST /api/v1/artifacts
      |
SHA-256 content-addressed /data/artifacts
      |
POST /api/v1/queue
      |
durable queue entry + dispatch_id
      |
POST .../dispatch
      |
PrintExecutionCapability
      |
accepted | indeterminate | failure
      |
explicit reconciliation when uncertain
```

Safety invariants:

- the public API never accepts an arbitrary server filesystem path;
- artifact content is bounded and hash-verified before queue creation;
- queue enqueue/dispatch/reconcile commands use authenticated principals and durable idempotency keys;
- `INDETERMINATE` means the previous side effect may have occurred and requires explicit reconciliation;
- a new dispatch request cannot bypass an uncertain state;
- same-key HTTP replays return the same logical queue resource rather than starting a second print;
- dispatch/reconcile HTTP commands are serialized in the current single-process runtime to close concurrent double-start races;
- receipt-bearing jobs are not redispatched;
- command audit stores a SHA-256 digest of the idempotency identity rather than the raw key.

Validation for this command layer includes Ruff lint/format on Python 3.12 and 3.13, the complete backend test suite (**171 tests passing** at the implementation merge gate), and unified container build/start/health/UI smoke validation. These automated gates do not replace physical printer testing.

## Inventory status

Implemented:

- spool metadata and archive state;
- editable empty-spool mass;
- exact `Decimal` serialization;
- immutable adjustment ledger for consumption, waste, return and correction;
- idempotency/conflicting-replay rejection;
- one spool per physical `(printer_id, slot_id)` and one slot per spool;
- opaque physical slot IDs without `spool_id` pollution in printer snapshots;
- SQLite WAL/foreign keys/restart durability;
- authenticated create/correct/move/unassign/archive command endpoints;
- live read DTOs consumed by the web UI.

Still required for automatic accounting:

- material reservation before dispatch;
- trustworthy per-material print usage estimates;
- queue-completion consumption worker;
- actual-vs-estimated reconciliation policy;
- stronger transaction/locking rules before multi-process execution.

## Hardware validation boundary

The largest remaining uncertainty is real hardware behavior rather than core architecture.

Bambu validation still needs documented real-device evidence for:

- LAN connection/reconnect and state synchronization;
- X2D project delivery and print-start acknowledgement;
- ambiguous-start/reconciliation behavior;
- lifecycle completion matching;
- X2D/N6 storage behavior;
- later AMS/drying/HMS/dual-nozzle capabilities.

Moonraker/OpenKE validation still needs documented real-device evidence for:

- API-key/auth configuration where applicable;
- HTTP/WebSocket connection and reconnect;
- live state subscriptions;
- G-code upload/checksum/start;
- lifecycle completion and failure handling.

Umbrel/Raspberry Pi validation still needs documented evidence for:

- representative Raspberry Pi 5/UmbrelOS installation/restart;
- Bambu X2D reachability from the actual Umbrel network environment;
- Ender/OpenKE/Moonraker reachability from that environment;
- persistence and upgrade behavior across later FoxForge package versions.

Documentation must not call these transports or the full deployment production-validated until those physical matrices pass.

## Current architecture and safety invariants

1. Common application/domain code must not import Bambu or Moonraker transport/protocol types.
2. Deep Bambu functionality remains available through typed Bambu capabilities rather than polluting common contracts.
3. Queue code never guesses whether an ambiguous print started; `INDETERMINATE` requires reconciliation and is never automatically retried.
4. Receipt-bearing jobs are never redispatched by retry logic or HTTP replay.
5. Inventory owns FoxForge spool identity; printer material snapshots expose physical material state and opaque slot IDs, not `spool_id`.
6. Public API DTOs expose FoxForge application contracts rather than raw vendor payloads, local paths or secrets.
7. Frontend code consumes typed FoxForge API models rather than Python modules or vendor transport structures.
8. Remote writes remain behind ADR 0004 authentication, authorization, validation, durable idempotency, normalized errors and audit.
9. Docker and Umbrel package the same FoxForge application behavior rather than divergent forks.
10. Umbrel App Proxy remains defense in depth; it is not a replacement for FoxForge command authorization.
11. Upstream-derived code/material must retain required license/copyright provenance; newly written FoxForge code remains distinguishable.
12. Bambuddy, PrintBuddy and PrintOps are specialized references, not FoxForge's base framework.
13. Scheduler/farm logic must depend on FoxForge capabilities and persisted application state, never directly on vendor transports.

## Recommended next sequence

1. **Queue UI integration:** browser-safe file selection → SHA-256 → artifact upload → enqueue → dispatch with explicit progress/error/`INDETERMINATE` UX and no client path assumptions.
2. **Physical alpha validation:** run Bambu LAN/X2D and Moonraker/OpenKE through connect → state → upload → print start → lifecycle → completion/reconciliation matrices and document results.
3. **Representative Umbrel validation:** install on Raspberry Pi 5/UmbrelOS, confirm restart/persistence and explicit-IP reachability to both real printer families.
4. **Common printer controls:** add pause/resume/cancel only through a typed common capability and ADR 0004 command semantics.
5. **Realtime application events:** define WebSocket/SSE reconnect/replay semantics and use them for TanStack Query cache updates without leaking vendor transports.
6. **Automatic filament accounting:** reservations, per-material estimates, queue-completion consumption and reconciliation.
7. **Farm scheduler:** persistent scheduling, printer selection, priorities/deadlines and durable lease/CAS semantics before distributed runners.
8. **Deep Bambu expansion:** AMS operations/drying, HMS, K profiles, dual nozzle and X2D-specific capabilities behind typed vendor interfaces.
9. **Additional vendors:** only after common contracts have been exercised on real Bambu and Moonraker/OpenKE hardware.

## Acceptance criteria for the next major alpha milestone

The next major alpha milestone should not be considered complete until:

- backend CI remains green on Python 3.12 and 3.13;
- frontend typecheck, tests and production build remain green;
- unified container startup smoke tests remain green;
- Umbrel package contract and anonymous amd64/arm64 runtime tests remain green;
- at least one real Bambu target and one real Moonraker/OpenKE target complete documented connectivity/state/print validation;
- representative Raspberry Pi 5/Umbrel installation, restart and persistence are documented;
- new write endpoints keep ADR 0004 auth/idempotency/audit semantics;
- API/application layers still contain no vendor transport imports;
- `INDETERMINATE` and receipt-bearing queue safety semantics remain preserved;
- inventory Decimal/idempotency/restart guarantees remain intact;
- architecture-significant work follows ADR 0003 upstream role/provenance rules;
- README, project status and deployment docs agree on what is released, what is only in `main`, and what is physically validated.
