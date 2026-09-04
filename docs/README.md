# FoxForge documentation

FoxForge treats the Git repository as the canonical source for durable architecture, implementation boundaries and current project state.

## Current project status

- [Project status](project-status.md) — dated snapshot of merged/current-source work, runtime maturity, validation boundaries, integration risks and recommended next steps.
- [`CHANGELOG.md`](../CHANGELOG.md) — implementation, architecture, validation and migration history.
- [`release/`](../release/) — durable metadata and release notes for published FoxForge versions.

The current published pre-release is **`v0.1.0-alpha.3`**. Current development source adds P1 common Pause/Resume/Cancel and P2 FoxForge-owned realtime application events over SSE with replay/resync semantics and TanStack Query invalidation. These post-alpha.3 changes are not part of the immutable alpha.3 image and require a later guarded release before versioned Docker/Umbrel users receive them. Physical printer/Raspberry Pi validation, automatic accounting and persistent farm scheduling remain incomplete.

## Independent audits

- [Independent project audit — 2026-09-04](audits/2026-09-04-independent-project-audit.md) — durable `AUD-*` remediation backlog covering release integrity, browser/deployment security, UI regressions, reproducible dependencies, persistence migrations, physical validation and roadmap sequencing.
- [Audit remediation tracker — 2026-09-04](audits/2026-09-04-remediation-tracker.md) — active implementation/evidence tracker. P3 remains frozen until the stabilization and resume gates are satisfied.

## Architecture Decision Records

- [ADR 0001: PrinterAdapter architecture](adr/0001-printer-adapter-architecture.md) — accepted. Defines the vendor-independent printer boundary, typed capability model and migration strategy for deep Bambu plus multi-vendor support.
- [ADR 0002: Repository layout](adr/0002-repository-layout.md) — accepted and implemented. Defines the top-level `backend/`, `frontend/` and `deployment/` ownership boundaries.
- [ADR 0003: Upstream architecture synthesis](adr/0003-upstream-architecture-synthesis.md) — accepted. Defines how Bambuddy, PrintBuddy and PrintOps are used as specialized references without becoming FoxForge's base framework.
- [ADR 0004: Command API security and idempotency](adr/0004-command-api-security.md) — accepted foundation for fail-closed command authentication, FoxForge principals/permissions, request correlation, durable idempotency, normalized command errors and audit.
- [ADR 0005: Browser command authentication and deployment trust](adr/0005-browser-command-authentication.md) — accepted. Supersedes ADR 0004's browser-auth deferral and forbids tokenless trusted-proxy bootstrap until an unspoofable proxy assertion contract exists. Current browser writes use an explicit memory-only operator command token.

## Core printer and fleet design

- [Printer contracts v1](design/printer-contracts.md) — normative `PrinterAdapter`, execution/material capabilities, normalized events/errors, idempotency semantics and contract tests.
- [AdapterRegistry and FleetService](design/fleet-service.md) — vendor-neutral adapter composition, fleet snapshots/capabilities, lifecycle and merged normalized events.
- [Common printer job control](design/job-control.md) — P1 `foxforge.job_control` v1 contract, exact vendor-job identity guards, Bambu/Moonraker mappings, ADR 0004 command semantics and browser uncertainty handling.
- [Realtime application events](design/realtime-events.md) — P2 application-event journal, SSE `Last-Event-ID` replay, fail-closed resynchronization, durable-write ordering and TanStack Query invalidation rules.
- [Upstream adoption map](design/upstream-adoption-map.md) — operational decision matrix for Bambu, multi-vendor, farm/scheduler, inventory, frontend and provenance work.

## Bambu Lab design

- [Bambu adapter foundation](design/bambu-adapter-foundation.md) — Bambu anti-corruption adapter boundary, state mapping, common capabilities and transport separation.
- [Bambu LAN production transport](design/bambu-lan-transport.md) — MQTT/TLS plus Bambu project delivery, sticky native state, verified upload, double busy guards and fail-safe ambiguous-start handling. Physical validation remains required before production support claims.
- [Bambu project storage strategy](design/bambu-project-storage.md) — Bambu-specific storage seam separating MQTT print control from FTPS or future validated X2D/N6 internal-eMMC delivery.

## Moonraker/Klipper design

- [Moonraker/Klipper adapter foundation](design/moonraker-adapter-foundation.md) — second real adapter family, common execution and external-spool material semantics.
- [Moonraker HTTP/WebSocket transport](design/moonraker-http-transport.md) — API-key auth, live state subscription, upload/start semantics and fail-safe indeterminate handling. Physical OpenKE/Moonraker validation remains required.

## Queue design

- [Queue dispatch and durable idempotency](design/queue-dispatch.md) — queue state machine, persisted dispatch crash boundary, reconciliation semantics and SQLite restart durability.
- [Queue event-driven print lifecycle](design/queue-event-lifecycle.md) — remote-job tracking from accepted dispatch through preparing, printing, pause/resume and terminal states with strict vendor-job identity matching.
- [Queue retry and single-pass runner policy](design/queue-retry-policy.md) — safe pre-start retry/backoff, one-entry-per-printer passes and protection of `DISPATCHING`, `INDETERMINATE` and receipt-bearing jobs.
- [Queue command API and artifact staging](design/queue-command-api.md) — authenticated artifact upload, enqueue/dispatch/reconciliation, HTTP replay semantics, command audit and single-process concurrency boundary. Released in `v0.1.0-alpha.3`.
- [Queue command UI](design/queue-command-ui.md) — browser hashing/staging/enqueue/dispatch workflow, `dispatch_id` versus HTTP idempotency identity, safe blocked/retryable-failure behavior and explicit `INDETERMINATE` reconciliation UX. Released in `v0.1.0-alpha.3`.

## Inventory design

- [Inventory foundation](design/inventory-foundation.md) — FoxForge-owned spool domain, immutable/idempotent mass ledger, opaque physical-slot assignments and separation from printer material state.
- [SQLite inventory persistence](design/inventory-sqlite.md) — durable exact-Decimal storage, restart/idempotency guarantees, assignment uniqueness and current single-container SQLite boundary.

## API and frontend design

- [Public API v1](design/public-api-v1.md) — the original versioned read foundation for health, fleet, queue and inventory. Later write endpoints follow ADR 0004/0005 and dedicated command designs.
- [ADR 0004](adr/0004-command-api-security.md) and [ADR 0005](adr/0005-browser-command-authentication.md) — application command security plus the current browser/deployment bootstrap boundary.
- [Common printer job control](design/job-control.md) — authenticated `printer.control` command plus capability-driven Pause/Resume/Cancel UI.
- [Realtime application events](design/realtime-events.md) — read-only application invalidation stream; canonical state remains the HTTP snapshots.
- [Queue command API and artifact staging](design/queue-command-api.md) — released backend command contract for safe queue writes without client filesystem paths.
- [Queue command UI](design/queue-command-ui.md) — released browser orchestration preserving the backend queue safety model.
- [Web UI foundation](design/web-ui-foundation.md) — React/TypeScript product structure, printer cockpit, Router/TanStack Query/i18next composition and vendor-neutral presentation rules.
- [Frontend parallel development policy](design/frontend-parallel-development.md) — main-driven UI development, query isolation, capability discipline and merge/CI rules while backend work proceeds in parallel.

Normal runtime consumes live FoxForge API models; demo data remains available only through explicit `?demo=1`. Current source uses an explicit operator command token held only in browser memory for protected writes. P2 adds same-origin SSE invalidations while keeping HTTP read models canonical and periodic polling as an alpha recovery fallback.

## Deployment

Deployment documentation lives in [`deployment/`](../deployment/README.md).

Current state:

- the unified Docker image and standalone Compose runtime are implemented;
- the same server process serves compiled SPA assets and `/api/v1`;
- persistent `/data` contains runtime configuration, SQLite state and staged queue artifacts;
- steady-state container execution is non-root;
- container startup smoke testing exists in CI and P2 extends it to verify `/api/v1/events`;
- standalone Docker protected writes require explicit `FOXFORGE_COMMAND_TOKEN`; omitting it is an intentional read-only deployment;
- tokenless `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is rejected until a cryptographically authenticated reverse-proxy bootstrap is designed and tested;
- `v0.1.0-alpha.3` publishes an immutable versioned Linux `amd64` + `arm64` GHCR image through the guarded release workflow;
- the historical `my3d-foxforge` alpha.3 package remains pinned to that immutable image; App Proxy is defense in depth, not an application principal;
- representative Raspberry Pi 5/UmbrelOS, reverse-proxy SSE and physical-printer validation are still required.

## Working rules

Architectural decisions belong in ADRs. Detailed interface contracts may live in design specifications linked from the relevant ADR.

Repository-level implementation guardrails are also summarized in [`AGENTS.md`](../AGENTS.md) so coding agents and contributors can discover the same canonical rules without relying on chat history.

Implementation PRs should:

1. start from current `main`;
2. preserve vendor-independent common boundaries and deep typed vendor capabilities;
3. use Bambuddy as the primary Bambu behavior reference, PrintBuddy as a multi-vendor/provider reference and PrintOps as an operations/farm reference, per ADR 0003;
4. define acceptance criteria and tests;
5. document important architecture/runtime changes in the repository;
6. preserve upstream copyright/license provenance where code or material is derived;
7. avoid claiming physical or production validation until the corresponding tests have actually been run;
8. keep remote mutations behind ADR 0004/0005 authentication, authorization, validation, idempotency, normalized-error and audit requirements.
