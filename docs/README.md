# FoxForge documentation

FoxForge treats the Git repository as the canonical source for durable architecture, implementation boundaries and current project state.

## Current project status

- [Project status](project-status.md) — concise current release/source/deployment state and development order.
- [Alpha 4.2 release evidence](status/alpha4-fix2-release-evidence-2026-09-05.md) — exact release commit/tag/workflow, browser artifact, GHCR OCI digest and Umbrel Store publication chain.
- [Physical validation runbook](testing/physical-validation-runbook.md) — exact published package target plus secret-safe Raspberry Pi/X2D/OpenKE evidence procedure.
- [`CHANGELOG.md`](../CHANGELOG.md) — implementation, architecture, validation and migration history.
- [`release/`](../release/) — durable metadata and release notes for published FoxForge versions.

The current published pre-release is **`v0.1.0-alpha.4.2`**, frozen at commit `fe5b3437f1e342548df74ded78557c771ef40710`.

Published multi-architecture image:

```text
ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6
```

The image supports Linux `amd64` and `arm64`. The matching `my3d-foxforge` `0.1.0-alpha.4.2` Umbrel package is merged in the companion Store at commit `e842c411e26689609e9bbba4681df903f3624bbd`.

The release includes the common Pause/Resume/Cancel foundation, FoxForge-owned realtime application events over SSE, the complete normal inventory operator workflow, audit/security stabilization and Alpha 4.2 responsive/browser-runtime fixes. Physical printer/Raspberry Pi validation, automatic filament accounting P3 and persistent farm scheduling remain incomplete. P3 is intentionally frozen in draft PR #58 until its physical/deployment resume gate is satisfied.

## Independent audits

- [Independent project audit — 2026-09-04](audits/2026-09-04-independent-project-audit.md) — immutable finding snapshot. It retains the release/main state that existed when the audit was performed.
- [Audit remediation tracker — 2026-09-04](audits/2026-09-04-remediation-tracker.md) — active implementation/evidence tracker. All software-only findings have remediation evidence; AUD-003 and AUD-013 remain validation-bound.

## Architecture Decision Records

- [ADR 0001: PrinterAdapter architecture](adr/0001-printer-adapter-architecture.md) — accepted. Defines the vendor-independent printer boundary, typed capability model and migration strategy for deep Bambu plus multi-vendor support.
- [ADR 0002: Repository layout](adr/0002-repository-layout.md) — accepted and implemented. Defines `backend/`, `frontend/` and `deployment/` ownership boundaries.
- [ADR 0003: Upstream architecture synthesis](adr/0003-upstream-architecture-synthesis.md) — accepted. Defines how Bambuddy, PrintBuddy and PrintOps are used as specialized references without becoming FoxForge's base framework.
- [ADR 0004: Command API security and idempotency](adr/0004-command-api-security.md) — fail-closed command authentication, FoxForge principals/permissions, correlation, durable idempotency, normalized command errors and audit.
- [ADR 0005: Browser command authentication and deployment trust](adr/0005-browser-command-authentication.md) — forbids tokenless trusted-proxy bootstrap until an unspoofable assertion contract exists. Current browser writes use an explicit operator token held only in memory.

## Core printer and fleet design

- [Printer contracts v1](design/printer-contracts.md) — normative `PrinterAdapter`, execution/material capabilities, normalized events/errors and idempotency semantics.
- [AdapterRegistry and FleetService](design/fleet-service.md) — vendor-neutral adapter composition, fleet snapshots/capabilities, lifecycle and merged normalized events.
- [Common printer job control](design/job-control.md) — `foxforge.job_control` v1, exact vendor-job identity guards, Bambu/Moonraker mappings and browser uncertainty handling.
- [Realtime application events](design/realtime-events.md) — SSE replay/resync, durable-write ordering and TanStack Query invalidation rules.
- [Upstream adoption map](design/upstream-adoption-map.md) — operational decision matrix for Bambu, multi-vendor, farm/scheduler, inventory, frontend and provenance work.

## Bambu Lab design

- [Bambu adapter foundation](design/bambu-adapter-foundation.md) — anti-corruption adapter boundary, state mapping, common capabilities and transport separation.
- [Bambu LAN production transport](design/bambu-lan-transport.md) — MQTT/TLS, project delivery, verified upload, busy guards and fail-safe ambiguous-start handling.
- [Bambu certificate trust](design/bambu-certificate-trust.md) — optional independent MQTT/FTPS SHA-256 pins, fail-closed mismatch semantics and physical validation requirements.
- [Bambu project storage strategy](design/bambu-project-storage.md) — storage seam separating MQTT print control from FTPS or future validated internal-storage delivery.

Physical X2D validation remains required before production support claims.

## Moonraker/Klipper design

- [Moonraker/Klipper adapter foundation](design/moonraker-adapter-foundation.md) — common execution and external-spool material semantics.
- [Moonraker HTTP/WebSocket transport](design/moonraker-http-transport.md) — API-key auth, live state subscription, upload/start semantics, endpoint security and fail-safe indeterminate handling.

Physical OpenKE/Moonraker validation remains required.

## Queue design

- [Queue dispatch and durable idempotency](design/queue-dispatch.md) — queue state machine, persisted dispatch crash boundary, reconciliation and SQLite restart durability.
- [Queue event-driven print lifecycle](design/queue-event-lifecycle.md) — remote-job tracking from accepted dispatch through preparing, printing, pause/resume and terminal states.
- [Queue retry and single-pass runner policy](design/queue-retry-policy.md) — safe pre-start retry/backoff and protection of `DISPATCHING`, `INDETERMINATE` and receipt-bearing jobs.
- [Queue command API and artifact staging](design/queue-command-api.md) — authenticated artifact upload, enqueue/dispatch/reconciliation, HTTP replay semantics and command audit.
- [Queue command UI](design/queue-command-ui.md) — browser hashing/staging/enqueue/dispatch workflow preserving backend safety semantics.

## Inventory design

- [Inventory foundation](design/inventory-foundation.md) — spool domain, immutable/idempotent mass ledger, opaque physical-slot assignments and separation from printer material state.
- [SQLite inventory persistence](design/inventory-sqlite.md) — exact-Decimal durability, restart/idempotency guarantees and assignment uniqueness.
- [Inventory atomicity](design/inventory-atomicity.md) — one atomic boundary for adjustment idempotency, balance validation and mutation.

The normal operator workflow — create, correct mass, edit empty-spool mass, assign/move/unassign, archive and history — is implemented and released. Automatic filament accounting remains a separate frozen P3 feature.

## API and frontend design

- [Public API v1](design/public-api-v1.md) — versioned read foundation for health, fleet, queue and inventory; later writes follow ADR 0004/0005.
- [Web UI foundation](design/web-ui-foundation.md) — React/TypeScript product structure, printer cockpit, Router/TanStack Query/i18next composition and vendor-neutral presentation rules.
- [Frontend parallel development policy](design/frontend-parallel-development.md) — main-driven UI development, query isolation, capability discipline and merge/CI rules.

Current Browser Acceptance covers phone 390×844, tablet 900×1024, desktop 1920×1080 and ultra-wide 5120×1440, including RU/UK layouts, Add Printer modal ownership/stacking/keyboard behavior, Operator Access and browser runtime errors. Normal runtime consumes live FoxForge API models; demo data remains explicit-only.

## Persistence and credentials

- [Persistence migrations](design/persistence-migrations.md) — current `config.json` schema version 2, SQLite `user_version` 1, backup/validation/rollback ownership.
- [Secret storage](design/secret-storage.md) — `SecretStore` boundary for Bambu access codes and Moonraker API keys; `/data` backups are credential-bearing data.
- [Artifact lifecycle](design/artifact-lifecycle.md) — content-addressed storage, quotas, free-space reserve, temp/orphan cleanup and queue-reference safety.

## Deployment

Deployment documentation lives in [`deployment/`](../deployment/README.md).

Current state:

- the unified Docker image and standalone Compose runtime are implemented;
- the same process serves compiled SPA assets and `/api/v1`;
- persistent `/data` contains runtime configuration, SQLite state, secrets and staged queue artifacts;
- steady-state container execution is non-root;
- standalone Docker protected writes require explicit `FOXFORGE_COMMAND_TOKEN`; omitting it is intentional read-only mode;
- tokenless `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is rejected;
- `v0.1.0-alpha.4.2` publishes an immutable Linux `amd64` + `arm64` GHCR image with SBOM/provenance;
- the companion Umbrel package pins that exact digest and maps Umbrel `APP_PASSWORD` to `FOXFORGE_COMMAND_TOKEN` for explicit memory-only **Unlock writes**;
- Store PR #28 and post-merge package/release gates are green;
- representative Raspberry Pi 5/UmbrelOS, real proxy/write path, printer-network reachability and physical-printer validation are still required before production claims.

## Physical validation and P3 gate

The exact current validation identity is maintained in:

- [Physical validation runbook](testing/physical-validation-runbook.md);
- [Physical evidence gate](testing/physical-evidence-gate.md).

Automated CI, QEMU, mocks and browser emulation are supporting evidence only and cannot close AUD-003 or AUD-013. Those findings remain `VALIDATION REQUIRED` until the real-device observations are collected and the evidence verifier passes.

P3 automatic filament accounting remains preserved in draft PR #58. The frozen-state/resume contract is [P3 frozen state](status/p3-frozen-state-2026-09-04.md). Do not merge P3 before the physical/deployment gate is satisfied.

## Working rules

Architectural decisions belong in ADRs. Detailed interface contracts may live in design specifications linked from the relevant ADR.

Repository-level implementation guardrails are summarized in [`AGENTS.md`](../AGENTS.md) so coding agents and contributors discover the same canonical rules without relying on chat history.

Implementation PRs should:

1. start from current `main`;
2. preserve vendor-independent common boundaries and deep typed vendor capabilities;
3. use Bambuddy as the primary Bambu behavior reference, PrintBuddy as a multi-vendor/provider reference and PrintOps as an operations/farm reference, per ADR 0003;
4. define acceptance criteria and tests;
5. document important architecture/runtime changes in the repository;
6. preserve upstream copyright/license provenance where code or material is derived;
7. avoid claiming physical or production validation until the corresponding tests have actually run;
8. keep remote mutations behind ADR 0004/0005 authentication, authorization, validation, idempotency, normalized-error and audit requirements.
