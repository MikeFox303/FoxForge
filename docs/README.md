# FoxForge documentation

FoxForge treats the Git repository as the canonical source for durable architecture, implementation boundaries and current project state.

## Current project status

- [Project status](project-status.md) — dated snapshot of merged/current-source work, runtime maturity, validation boundaries, integration risks and recommended next steps.
- [`CHANGELOG.md`](../CHANGELOG.md) — implementation, architecture, validation and migration history.
- [`release/`](../release/) — durable metadata and release notes for published FoxForge versions.

The current published pre-release is **`v0.1.0-alpha.2`**. Development source has moved beyond that immutable image with authenticated printer configuration, inventory mutations, audited artifact/queue commands and the browser-safe queue upload/enqueue/dispatch/reconciliation workflow. Physical printer/Raspberry Pi validation, realtime delivery, automatic accounting, common print controls and persistent farm scheduling remain incomplete.

## Architecture Decision Records

- [ADR 0001: PrinterAdapter architecture](adr/0001-printer-adapter-architecture.md) — accepted. Defines the vendor-independent printer boundary, typed capability model and migration strategy for deep Bambu plus multi-vendor support.
- [ADR 0002: Repository layout](adr/0002-repository-layout.md) — accepted and implemented. Defines the top-level `backend/`, `frontend/` and `deployment/` ownership boundaries.
- [ADR 0003: Upstream architecture synthesis](adr/0003-upstream-architecture-synthesis.md) — accepted. Defines how Bambuddy, PrintBuddy and PrintOps are used as specialized references without becoming FoxForge's base framework.
- [ADR 0004: Command API security and idempotency](adr/0004-command-api-security.md) — accepted. Defines fail-closed command authentication, FoxForge principals/permissions, request correlation, durable idempotency, normalized command errors, audit expectations and the safe mutation rollout sequence.

## Core printer and fleet design

- [Printer contracts v1](design/printer-contracts.md) — normative `PrinterAdapter`, execution/material capabilities, normalized events/errors, idempotency semantics and contract tests.
- [AdapterRegistry and FleetService](design/fleet-service.md) — vendor-neutral adapter composition, fleet snapshots/capabilities, lifecycle and merged normalized events.
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
- [Queue command API and artifact staging](design/queue-command-api.md) — authenticated artifact upload, enqueue/dispatch/reconciliation, HTTP replay semantics, command audit and single-process concurrency boundary.
- [Queue command UI](design/queue-command-ui.md) — browser hashing/staging/enqueue/dispatch workflow, `dispatch_id` versus HTTP idempotency identity, safe blocked/retryable-failure behavior and explicit `INDETERMINATE` reconciliation UX.

## Inventory design

- [Inventory foundation](design/inventory-foundation.md) — FoxForge-owned spool domain, immutable/idempotent mass ledger, opaque physical-slot assignments and separation from printer material state.
- [SQLite inventory persistence](design/inventory-sqlite.md) — durable exact-Decimal storage, restart/idempotency guarantees, assignment uniqueness and current single-container SQLite boundary.

## API and frontend design

- [Public API v1](design/public-api-v1.md) — the original versioned read foundation for health, fleet, queue and inventory. Later write endpoints follow ADR 0004 and dedicated command designs rather than weakening the original read DTO boundary.
- [ADR 0004: Command API security and idempotency](adr/0004-command-api-security.md) — fail-closed authentication, permissions, idempotency, errors and audit contract for remote mutations.
- [Queue command API and artifact staging](design/queue-command-api.md) — implemented backend command contract for safe queue writes without client filesystem paths.
- [Queue command UI](design/queue-command-ui.md) — implemented browser orchestration preserving the backend queue safety model.
- [Web UI foundation](design/web-ui-foundation.md) — React/TypeScript product structure, printer cockpit, Router/TanStack Query/i18next composition and vendor-neutral presentation rules.
- [Frontend parallel development policy](design/frontend-parallel-development.md) — main-driven UI development, query isolation, capability discipline and merge/CI rules while backend work proceeds in parallel.

Normal runtime consumes live FoxForge API models; demo data remains available only through explicit `?demo=1`. Browser operator sessions now support printer setup and queue command workflows. Realtime WebSocket/SSE remains a separate future contract.

## Deployment

Deployment documentation lives in [`deployment/`](../deployment/README.md).

Current state:

- the unified Docker image and standalone Compose runtime are implemented;
- the same server process serves compiled SPA assets and `/api/v1`;
- persistent `/data` contains runtime configuration, SQLite state and staged queue artifacts;
- steady-state container execution is non-root;
- container startup smoke testing exists in CI;
- `v0.1.0-alpha.2` publishes an immutable versioned Linux `amd64` + `arm64` GHCR image through the guarded release workflow;
- anonymous pull/start/runtime smoke validation passes for both architectures in CI;
- the `my3d-foxforge` package is published in `MikeFox303/umbrel-3d-printing-store` behind authenticated Umbrel App Proxy and pins the immutable `alpha.2` digest;
- post-`alpha.2` source work requires a later guarded release before Docker/Umbrel users receive it;
- representative Raspberry Pi 5/UmbrelOS and physical-printer validation are still required.

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
8. keep remote mutations behind ADR 0004 authentication, authorization, validation, idempotency, normalized-error and audit requirements.
