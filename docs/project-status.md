# FoxForge project status

**Snapshot date:** 2026-09-04  
**Canonical branch:** `main` after publication of `v0.1.0-alpha.3`  
**Published pre-release:** `v0.1.0-alpha.3` (`0.1.0a3` backend package)  
**Umbrel Community App:** `my3d-foxforge` in `MikeFox303/umbrel-3d-printing-store`, pinned to the immutable `alpha.3` multi-architecture digest  
**Maturity:** runnable/installable alpha; not production-ready

This document is the concise current-source snapshot for FoxForge. ADRs and design specifications remain normative for architecture; `CHANGELOG.md` remains implementation history; `release/` contains durable release metadata and notes.

The published `alpha.3` image is immutable. The current functional source state matches the `alpha.3` release line; future source changes require a later guarded release before Docker/Umbrel users receive them.

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, normalized snapshots/events/errors and typed capability discovery. |
| Printer adapters | Implemented foundation | Bambu and Moonraker coexist behind vendor-neutral contracts. |
| Fleet management | Implemented | Dynamic composition, lifecycle, snapshots, capabilities and normalized events. |
| Durable print queue | Implemented foundation | SQLite-backed dispatch/idempotency, explicit `INDETERMINATE`, lifecycle tracking and terminal persistence. |
| Queue retry runner | Implemented | Bounded pre-start retries; uncertain or receipt-bearing jobs are never blindly retried. |
| Filament/spool inventory | Durable foundation implemented | Exact `Decimal` ledger, idempotent adjustments, physical assignments and restart durability. |
| Public HTTP API v1 reads | Implemented | Health, fleet, queue and inventory read models without raw vendor payloads or local paths. |
| Command API security | Released foundation in alpha.3 | Fail-closed command auth, permissions, request IDs, normalized errors, durable idempotency and audit. |
| Printer configuration writes | Released in alpha.3 | Authenticated add/update/remove/test/reconnect flows plus browser setup UI. |
| Inventory writes | Released in alpha.3 | Authenticated/idempotent create/correct/empty-mass/move/unassign/archive commands. |
| Queue write API | Released in alpha.3 | Content-addressed artifact staging plus authenticated/idempotent enqueue, dispatch and explicit reconciliation. |
| Queue command UI | Released in alpha.3 | Browser SHA-256, byte-only staging, durable enqueue, explicit dispatch, safe retryability and `INDETERMINATE` reconciliation. |
| Command audit | Released in alpha.3 | Append-only SQLite audit with non-secret idempotency digests. |
| Alpha runtime | Implemented | Single `aiohttp` server, offline-safe printer composition, reconnect supervision, SPA + API and persistent `/data`. |
| Web UI | Functional alpha | Live reads, printer setup and queue command workflow are released; realtime and full inventory mutation UI remain incomplete. |
| Bambu LAN transport | Implemented, hardware validation pending | Automated coverage exists; real X2D validation is still required. |
| Moonraker transport | Implemented, hardware validation pending | Automated coverage exists; real OpenKE/Moonraker validation is still required. |
| Docker/Umbrel | Runnable alpha implemented | Immutable `alpha.3` is shipped for `amd64` + `arm64`; representative Raspberry Pi 5 validation is pending. |
| Realtime API | Not implemented | WebSocket/SSE application-event delivery remains future work. |
| Common pause/resume/cancel | Not implemented on main | Requires a typed common capability plus ADR 0004 command semantics before UI controls. A divergent development branch exists and must be reconciled with current `main` before reuse. |
| Automatic filament accounting | Not implemented | Queue completion is not yet tied to spool reservations/consumption reconciliation. |
| Farm scheduler | Not implemented | Persistent scheduling, selection, deadlines and durable leases remain pending. |

## Browser queue command boundary

The released `alpha.3` flow is:

```text
browser File
      |
WebCrypto SHA-256
      |
POST /api/v1/artifacts
(bytes + filename + expected hash; no client path)
      |
SHA-256 content-addressed /data/artifacts
      |
POST /api/v1/queue
(queueId + durable dispatchId)
      |
durable queue entry
      |
explicit POST .../dispatch
      |
accepted | blocked | retryable pre-start failure | indeterminate
                                                  |
                                      explicit reconciliation only
```

Safety invariants:

- the browser and public API never pass an arbitrary client/server filesystem path;
- artifact content is bounded and hash-verified before queue creation;
- queue enqueue/dispatch/reconcile commands use authenticated principals and durable HTTP idempotency records;
- queue `dispatch_id` and HTTP `Idempotency-Key` are distinct identities;
- an uncertain HTTP request replay keeps the same key;
- a conclusive `BLOCKED` response may later be intentionally reassessed with a new HTTP key while preserving the original queue `dispatch_id`;
- a receipt-free `FAILED` entry exposes retry only when the backend marks its error `retryable=true`;
- `INDETERMINATE` requires explicit reconciliation and cannot be bypassed with another dispatch request;
- receipt-bearing jobs are not redispatched;
- command audit stores a SHA-256 digest of the HTTP idempotency identity rather than the raw key.

See [Queue command API and artifact staging](design/queue-command-api.md) and [Queue command UI](design/queue-command-ui.md).

## Validation status

The guarded `v0.1.0-alpha.3` release validation passed on the exact frozen release commit:

- release manifest/version consistency;
- backend installation on the supported release environment;
- Ruff lint and formatting checks;
- **171 backend tests**;
- frontend installation and TypeScript typecheck;
- **28 frontend tests**;
- Vite production build;
- unified release-image build and live `/healthz`/SPA/persistence smoke checks;
- Linux `amd64` + `arm64` multi-architecture publication with SBOM/provenance metadata;
- Git tag and GitHub pre-release creation only after the preceding gates succeeded.

The companion Umbrel package was updated to the immutable `alpha.3` multi-architecture digest and passed package/Compose validation plus anonymous runtime smoke tests on both `linux/amd64` and `linux/arm64`.

These automated gates validate architecture, packaging and replay behavior but do not replace physical printer testing.

## Hardware validation boundary

Bambu still needs documented real-device evidence for LAN connection/reconnect, state synchronization, X2D project delivery, print-start acknowledgement, ambiguous-start reconciliation, lifecycle completion and X2D/N6 storage behavior.

Moonraker/OpenKE still needs documented real-device evidence for authentication where applicable, HTTP/WebSocket connection/reconnect, live subscriptions, G-code upload/checksum/start and lifecycle completion/failure handling.

Umbrel/Raspberry Pi still needs documented evidence for Raspberry Pi 5 installation/restart, X2D and OpenKE reachability from the actual Umbrel network, persistence and upgrades.

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
9. Browser command code does not invent weaker retry semantics than the backend queue contract.
10. Docker and Umbrel package the same FoxForge application behavior rather than divergent forks.
11. Umbrel App Proxy remains defense in depth; it is not a replacement for FoxForge command authorization.
12. Upstream-derived code/material must retain required license/copyright provenance; newly written FoxForge code remains distinguishable.
13. Bambuddy, PrintBuddy and PrintOps are specialized references, not FoxForge's base framework.
14. Scheduler/farm logic must depend on FoxForge capabilities and persisted application state, never directly on vendor transports.

## Development sequence after alpha.3

P0 is documentation/release-state synchronization. It is complete when README, this project-status snapshot, documentation index and active design specifications agree that `v0.1.0-alpha.3` is the current published release, while historical alpha.2 release/validation/ADR context remains unchanged.

After P0, continue in this order:

1. **P1 — Common printer controls:** reconcile the existing `feature/job-control-capability` work onto current `main`, then implement pause/resume/cancel through a typed common capability plus ADR 0004 command semantics and UI controls.
2. **P2 — Realtime application events:** define WebSocket/SSE reconnect/replay semantics and update TanStack Query caches without vendor transport leakage.
3. **P3 — Automatic filament accounting:** add reservations, estimates, queue-completion consumption and explicit reconciliation.
4. **P4 — Inventory mutation UI:** expose guarded spool create/correct/assignment/archive flows above the already released command API.
5. **Physical validation throughout:** Bambu LAN/X2D and Moonraker/OpenKE connect → state → upload → print start → controls → lifecycle → completion/reconciliation, plus Raspberry Pi 5/Umbrel install/restart/persistence/reachability.
6. **P5 — Farm scheduler:** persistent scheduling, printer selection, priorities/deadlines and durable lease/CAS semantics after queue/control/realtime/inventory foundations are stable.
7. **P6 — Deep Bambu expansion:** AMS operations/drying, HMS, K profiles, dual nozzle and X2D-specific capabilities behind typed vendor interfaces.

## Acceptance criteria for P0

- `README.md` reports `v0.1.0-alpha.3` as the published release;
- `docs/README.md` reports the same release and deployment state;
- `docs/project-status.md` reports `alpha.3` and no longer labels released alpha.3 features as post-alpha.2 development work;
- active UI/queue design documents describe the alpha.3 implementation as released rather than post-alpha.2 source work;
- Umbrel documentation references the immutable alpha.3 package/digest state where the current package is described;
- historical `release/v0.1.0-alpha.2.md`, alpha.2 validation evidence, CHANGELOG history and ADR 0004 decision context remain historically accurate rather than being rewritten;
- a repository search for `alpha.2` leaves only historically intentional references.

## Acceptance criteria for the next major alpha milestone

- backend CI remains green on Python 3.12 and 3.13;
- frontend typecheck, tests and production build remain green;
- unified container startup smoke tests remain green;
- Umbrel package contract and anonymous amd64/arm64 runtime tests remain green;
- at least one real Bambu target and one real Moonraker/OpenKE target complete documented connectivity/state/print validation;
- representative Raspberry Pi 5/Umbrel installation, restart and persistence are documented;
- new write endpoints keep ADR 0004 auth/idempotency/audit semantics;
- API/application layers still contain no vendor transport imports;
- `INDETERMINATE` and receipt-bearing queue safety semantics remain preserved in backend and UI;
- inventory Decimal/idempotency/restart guarantees remain intact;
- README, project status and deployment docs agree on what is released, what is only in source, and what is physically validated.
