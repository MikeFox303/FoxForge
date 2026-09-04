# FoxForge documentation

FoxForge treats the Git repository as the canonical source for durable architecture, implementation boundaries and current project state.

## Current project status

- [Project status](project-status.md) — dated snapshot of merged `main` work, runtime maturity, validation boundaries, integration risks and recommended next steps.
- [`CHANGELOG.md`](../CHANGELOG.md) — implementation, architecture, validation and migration history.
- [`release/`](../release/) — durable metadata and release notes for published FoxForge versions.

The current published pre-release is **`v0.1.0-alpha.2`**. Backend, live read API, web UI, SQLite queue/inventory persistence, authenticated printer/inventory/queue command foundations, Docker runtime, versioned Linux `amd64`/`arm64` image publication and the user-managed Umbrel Community App package are integrated. Physical printer/Raspberry Pi validation, common pause/resume/cancel controls, realtime delivery, automatic accounting and persistent farm scheduling remain incomplete.

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
- [Queue command API and artifact staging](design/queue-command-api.md) — authenticated content-addressed upload, enqueue/dispatch/reconcile HTTP commands, command audit and the single-process concurrency guard.

## Inventory design

- [Inventory foundation](design/inventory-foundation.md) — FoxForge-owned spool domain, immutable/idempotent mass ledger, opaque physical-slot assignments and separation from printer material state.
- [SQLite inventory persistence](design/inventory-sqlite.md) — durable exact-Decimal storage, restart/idempotency guarantees, assignment uniqueness and current single-container SQLite boundary.

## API and frontend design

- [Public API v1 read foundation](design/public-api-v1.md) — versioned `/api/v1` read contract for health, fleet, queue and inventory without raw vendor payloads or secret leakage. Later command endpoints extend the same namespace under ADR 0004.
- [ADR 0004: Command API security and idempotency](adr/0004-command-api-security.md) — security contract governing all remote state-changing routes.
- [Queue command API and artifact staging](design/queue-command-api.md) — current queue write contract and artifact upload boundary.
- [Web UI foundation](design/web-ui-foundation.md) — React/TypeScript product structure, printer cockpit, Router/TanStack Query/i18next composition and vendor-neutral presentation rules.
- [Frontend parallel development policy](design/frontend-parallel-development.md) — main-driven UI development, query isolation, capability discipline and merge/CI rules while backend work proceeds in parallel.

The production alpha UI consumes live `/api/v1` read models and can manage printer connections through the trusted browser command-session boundary when the deployment enables it. Authenticated inventory and queue mutation APIs are implemented at the backend boundary, but full browser spool/print workflows remain incomplete. Realtime WebSocket/SSE delivery is still a separate future contract.

## Deployment

Deployment documentation lives in [`deployment/`](../deployment/README.md).

Current state:

- the unified Docker image and standalone Compose runtime are implemented;
- the same server process serves compiled SPA assets and `/api/v1`;
- persistent `/data` contains runtime configuration, SQLite state and staged print artifacts;
- command idempotency and append-only command audit are persisted in SQLite;
- steady-state container execution is non-root;
- container startup smoke testing exists in CI;
- `v0.1.0-alpha.2` publishes an immutable versioned Linux `amd64` + `arm64` GHCR image through the guarded release workflow;
- anonymous pull/start/runtime smoke validation passes for both architectures in CI;
- the `my3d-foxforge` package is published in `MikeFox303/umbrel-3d-printing-store` behind authenticated Umbrel App Proxy and pins the immutable `alpha.2` digest;
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
8. keep remote mutations disabled unless they satisfy ADR 0004 authentication, authorization, validation, idempotency, normalized-error and audit requirements.
