# FoxForge project status

**Snapshot date:** 2026-09-04  
**Canonical branch:** `main`  
**Source snapshot:** `v0.1.0-alpha.3` plus completed P1 common job-control and P2 realtime application-event work  
**Published pre-release:** `v0.1.0-alpha.3` (`0.1.0a3` backend package)  
**Umbrel Community App:** `my3d-foxforge` in `MikeFox303/umbrel-3d-printing-store`, pinned to the immutable `alpha.3` multi-architecture digest  
**Maturity:** runnable/installable alpha; not production-ready

This document is the concise current-source snapshot for FoxForge. ADRs and design specifications remain normative for architecture; `CHANGELOG.md` remains implementation history; `release/` contains durable release metadata and notes.

The published `alpha.3` image is immutable. Current source contains the P1 common printer-control vertical slice and P2 realtime application-event layer described below. Those post-alpha.3 changes require a later guarded release before versioned Docker/Umbrel users receive them.

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
| Common pause/resume/cancel | Implemented post-alpha.3 (P1) | Typed `foxforge.job_control` v1 capability, exact vendor-job identity guards, Bambu/Moonraker transports, ADR 0004 command API, audit/idempotency and capability-driven browser controls. Physical validation pending. |
| Realtime application events | Implemented post-alpha.3 (P2) | FoxForge-owned SSE journal, epoch/sequence replay, explicit resync, durable queue/inventory/configuration topics and TanStack Query invalidation bridge. Polling remains fallback. |
| Alpha runtime | Implemented | Single `aiohttp` server, offline-safe printer composition, reconnect supervision, SPA + API, P2 SSE and persistent `/data`. |
| Web UI | Functional alpha | Live reads, printer setup, queue commands, P1 controls and P2 realtime cache invalidation are implemented; full inventory mutation UI remains incomplete. |
| Bambu LAN transport | Implemented, hardware validation pending | Automated coverage includes control-command safety; real X2D pause/resume/cancel validation is still required. |
| Moonraker transport | Implemented, hardware validation pending | Automated coverage includes control endpoints; real OpenKE/Moonraker pause/resume/cancel validation is still required. |
| Docker/Umbrel | Runnable alpha implemented | Immutable `alpha.3` is shipped for `amd64` + `arm64`; current P1/P2 source is not released yet; representative Raspberry Pi 5 validation is pending. |
| Automatic filament accounting | Not implemented | Queue completion is not yet tied to spool reservations/consumption reconciliation. |
| Farm scheduler | Not implemented | Persistent scheduling, selection, deadlines and durable leases remain pending. |

## P1 common job-control boundary

P1 adds one common typed capability rather than three vendor-specific UI paths:

```text
React printer cockpit
        |
POST /api/v1/printers/{printer_id}/job-control
Authorization + Idempotency-Key + command audit
        |
FleetService.capability(JobControlCapability)
        |
exact expectedVendorJobId + normalized job-state guard
        |
     +--+------------------+
     |                     |
BambuJobControl       MoonrakerJobControl
     |                     |
pause/resume/stop     /pause /resume /cancel
```

Safety rules:

- `controlId` is the logical FoxForge control identity and is distinct from HTTP `Idempotency-Key`;
- every control command names the exact vendor job identity observed before the operator acts;
- stale/offline/no-job/no-identity/mismatched-job/invalid-state requests are blocked before a transport side effect;
- Bambu and Moonraker transports re-check the native current job identity immediately before sending the command;
- a conclusive completed HTTP replay never executes the adapter side effect a second time;
- a transport `INDETERMINATE` leaves HTTP idempotency unresolved (`STARTED`); replaying that same HTTP key returns reconciliation-required without executing the adapter again;
- the browser never automatically retries an uncertain pause/resume/cancel; ordinary polling timestamps do not unlock controls, which remain blocked until the observed job state or vendor job identity changes conclusively;
- cancel requires explicit operator confirmation;
- the UI renders actions from `foxforge.job_control` metadata, not from vendor/model-name inference.

See [Common printer job control](design/job-control.md).

## P2 realtime application-event boundary

P2 keeps versioned HTTP snapshots canonical and adds an application-level invalidation stream:

```text
normalized FleetService events ----+
                                    |
durable QueueStore writes ---------+--> ApplicationEventJournal
                                    |      streamEpoch + sequence
inventory durable writes -----------+              |
                                    |       GET /api/v1/events (SSE)
printer config add/update/remove ---+              |
                                                   v
                                          browser EventSource
                                                   |
                                         TanStack Query invalidation
                                                   |
                                       canonical HTTP snapshot refresh
```

Realtime safety rules:

- SSE carries FoxForge application topics only; it does not expose Bambu MQTT payloads, Moonraker WebSocket/JSON-RPC payloads, secrets or vendor transport objects;
- each process owns a random stream epoch and monotonically increasing sequence;
- reconnect through a retained `Last-Event-ID` replays missed changes in order and then emits `ready`;
- fresh, restarted, malformed, future, expired or subscriber-overflow cursors emit `resync_required` instead of pretending continuity;
- `resync_required` invalidates fleet, queue and inventory HTTP snapshots immediately;
- queue/inventory realtime events are emitted only after the corresponding durable store mutation succeeds;
- failed durable writes do not advance the event journal;
- the application event relay subscribes before printer reconnect supervision starts, preventing startup connection-event loss;
- high-frequency browser invalidations are coalesced over 250 ms to limit request storms;
- normal polling remains enabled as an alpha fallback until representative deployment/browser validation justifies reducing it.

See [Realtime application events](design/realtime-events.md).

## Browser queue command boundary

The released `alpha.3` flow remains:

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

Queue safety invariants remain unchanged:

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

P1 adds dedicated automated coverage for common eligibility/state identity rules, Bambu/Moonraker action translation, non-retryable ambiguous transport outcomes, authenticated HTTP command execution, durable replay/idempotency conflict behavior, command audit, frontend command identity separation and EN/RU/UK job-control translation parity. P1 backend gates pass on Python 3.12 and 3.13, the Web UI gate passes, and the unified-container build/start/health/UI smoke gate passes on the P1 merge candidate and merge commit.

P2 adds automated coverage for stream replay/resync, replay gaps, process-epoch mismatch, slow subscribers, durable-write event ordering, failed-write non-publication, printer configuration events, SSE headers/payloads and frontend query-family routing. The unified-container smoke opens `/api/v1/events` and requires the initial `resync_required` application contract. The P2 merge candidate passed Ruff plus the backend suite on Python 3.12/3.13, Web UI typecheck/tests/build and unified-container SSE smoke before PR #57 was considered ready for merge.

The companion Umbrel package remains pinned to the immutable `alpha.3` multi-architecture digest and passed package/Compose validation plus anonymous runtime smoke tests on both `linux/amd64` and `linux/arm64` for that released image.

Automated gates validate architecture, packaging and replay behavior but do not replace physical printer testing.

## Hardware validation boundary

Bambu still needs documented real-device evidence for LAN connection/reconnect, state synchronization, X2D project delivery, print-start acknowledgement, pause → observed pause, resume → observed printing, cancel → observed terminal state, ambiguous control outcomes, lifecycle completion and X2D/N6 storage behavior.

Moonraker/OpenKE still needs documented real-device evidence for authentication where applicable, HTTP/WebSocket connection/reconnect, live subscriptions, G-code upload/checksum/start, pause/resume/cancel, ambiguous control outcomes and lifecycle completion/failure handling.

Umbrel/Raspberry Pi still needs documented evidence for Raspberry Pi 5 installation/restart, X2D and OpenKE reachability from the actual Umbrel network, persistence, upgrades and representative reverse-proxy/browser SSE behavior.

Documentation must not call these transports or the full deployment production-validated until those physical matrices pass.

## Current architecture and safety invariants

1. Common application/domain code must not import Bambu or Moonraker transport/protocol types.
2. Deep Bambu functionality remains available through typed Bambu capabilities rather than polluting common contracts.
3. Common job controls target an exact observed vendor job identity; FoxForge never sends pause/resume/cancel to an unidentified or mismatched active job.
4. Ambiguous job-control side effects are non-retryable; same-key unresolved HTTP replay never repeats the device command.
5. Queue code never guesses whether an ambiguous print started; `INDETERMINATE` requires reconciliation and is never automatically retried.
6. Receipt-bearing jobs are never redispatched by retry logic or HTTP replay.
7. Realtime events are application invalidations, not an alternate source of truth; replay uncertainty forces HTTP snapshot resync.
8. Durable queue/inventory events are emitted only after successful persistence; failed writes do not publish state changes.
9. Inventory owns FoxForge spool identity; printer material snapshots expose physical material state and opaque slot IDs, not `spool_id`.
10. Public API DTOs expose FoxForge application contracts rather than raw vendor payloads, local paths or secrets.
11. Frontend code consumes typed FoxForge API models rather than Python modules or vendor transport structures.
12. Remote writes remain behind ADR 0004 authentication, authorization, validation, durable idempotency, normalized errors and audit.
13. Browser command code does not invent weaker retry semantics than backend command contracts.
14. Docker and Umbrel package the same FoxForge application behavior rather than divergent forks.
15. Umbrel App Proxy remains defense in depth; it is not a replacement for FoxForge command authorization.
16. Upstream-derived code/material must retain required license/copyright provenance; newly written FoxForge code remains distinguishable.
17. Bambuddy, PrintBuddy and PrintOps are specialized references, not FoxForge's base framework.
18. Scheduler/farm logic must depend on FoxForge capabilities and persisted application state, never directly on vendor transports.

## Development sequence after alpha.3

- **P0 — Documentation/release synchronization:** complete and merged as PR #55.
- **P1 — Common printer controls:** complete and merged as PR #56; typed Pause/Resume/Cancel, Bambu/Moonraker mappings, guarded command API, audit/idempotency and browser controls. Automated validation is green; physical validation remains a separate production-readiness requirement.
- **P2 — Realtime application events:** software-complete through PR #57; SSE reconnect/replay/resync semantics, durable application topics and TanStack Query invalidation are implemented without vendor transport leakage. Representative deployment/browser validation remains a separate alpha-readiness task.
- **P3 — Automatic filament accounting:** next implementation priority; reservations, estimates, queue-completion consumption and explicit reconciliation.
- **P4 — Inventory mutation UI:** guarded spool create/correct/assignment/archive flows above the already released command API.
- **Physical validation throughout:** Bambu LAN/X2D and Moonraker/OpenKE connect → state → upload → print start → controls → lifecycle → completion/reconciliation, plus Raspberry Pi 5/Umbrel install/restart/persistence/reachability/realtime behavior.
- **P5 — Farm scheduler:** persistent scheduling, printer selection, priorities/deadlines and durable lease/CAS semantics after queue/control/realtime/inventory foundations are stable.
- **P6 — Deep Bambu expansion:** AMS operations/drying, HMS, K profiles, dual nozzle and X2D-specific capabilities behind typed vendor interfaces.

## Acceptance criteria for P1

- typed `foxforge.job_control` v1 exists in the common domain and advertises supported actions;
- Bambu and Moonraker adapters expose it through `PrinterAdapter.capability()`;
- Bambu maps common cancel to native stop while Moonraker maps cancel to its print-cancel endpoint;
- exact vendor-job identity is checked in common assessment and again at the native transport boundary;
- `/api/v1/fleet` advertises job-control capability/action metadata;
- `POST /api/v1/printers/{printer_id}/job-control` requires `printer.control`, request validation and `Idempotency-Key`;
- command audit covers job-control requests before side effects;
- completed same-key replay is side-effect-free;
- unresolved/indeterminate same-key replay is side-effect-free and requires state reconciliation;
- frontend controls are capability/state gated and cancel asks for confirmation;
- frontend uncertainty handling never blind-retries a device control and is not cleared by polling timestamps alone;
- EN/RU/UK job-control key parity is tested;
- backend Ruff/tests, frontend typecheck/tests/build and unified-container smoke are green;
- physical X2D/OpenKE control validation remains explicitly pending until performed.

## Acceptance criteria for P2

- application events are FoxForge-owned and vendor-neutral;
- `GET /api/v1/events` uses SSE and supports `Last-Event-ID` replay within a bounded current-process journal;
- stream epoch/sequence continuity is explicit and restart/replay gaps require resync;
- queue and inventory event publication follows successful durable writes, never precedes them;
- failed durable writes emit no realtime state-change event;
- printer configuration changes and normalized fleet changes propagate through application topics;
- the browser invalidates the correct TanStack Query families and unknown/malformed events fail closed to full resync;
- high-frequency events are batched so progress telemetry does not create uncontrolled refetch traffic;
- HTTP snapshots remain canonical and polling remains an alpha fallback;
- backend Ruff/tests pass on Python 3.12/3.13;
- frontend typecheck/tests/build pass;
- unified-container smoke verifies the SSE endpoint in the packaged application;
- no vendor transport imports/payloads leak into API/frontend realtime contracts;
- P2 docs and changelog are synchronized.

## Acceptance criteria for the next major alpha milestone

- backend CI remains green on Python 3.12 and 3.13;
- frontend typecheck, tests and production build remain green;
- unified container startup smoke tests remain green, including P2 SSE reachability;
- Umbrel package contract and anonymous amd64/arm64 runtime tests remain green;
- at least one real Bambu target and one real Moonraker/OpenKE target complete documented connectivity/state/print/control validation;
- representative Raspberry Pi 5/Umbrel installation, restart, persistence and realtime reverse-proxy behavior are documented;
- new write endpoints keep ADR 0004 auth/idempotency/audit semantics;
- API/application layers still contain no vendor transport imports;
- `INDETERMINATE` safety semantics remain preserved in backend and UI;
- inventory Decimal/idempotency/restart guarantees remain intact;
- README, project status and deployment docs agree on what is released, what is only in source, and what is physically validated.
