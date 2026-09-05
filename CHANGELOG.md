# Changelog

All notable FoxForge changes are recorded here. The Git repository remains the canonical project history; this file summarizes user-visible, release and architectural milestones rather than every intermediate commit.

FoxForge has not published a stable release yet. Alpha releases are versioned below. Detailed implementation history remains available in Git history, ADRs and design documents under `docs/`.

## Unreleased

- Documentation synchronized after the `v0.1.0-alpha.4` guarded release and companion Umbrel package update. No additional application behavior is implied by documentation-only commits.

## [0.1.0-alpha.4] - 2026-09-05

Fourth public FoxForge pre-release. `alpha.4` packages P1 common job control, P2 realtime application events, the complete normal inventory operator workflow and the independent-audit stabilization/security foundation. See [`release/v0.1.0-alpha.4.md`](release/v0.1.0-alpha.4.md) for the full immutable release notes.

### Added

- Common typed `foxforge.job_control` v1 capability for Pause, Resume and Cancel with exact observed vendor-job identity guards.
- Bambu LAN pause/resume/stop mapping and Moonraker `/printer/print/pause`, `/resume`, `/cancel` mapping with native job-identity revalidation.
- Guarded `POST /api/v1/printers/{printer_id}/job-control` command with `printer.control`, durable HTTP idempotency and command audit.
- FoxForge-owned application event journal with process epoch, monotonic sequence cursors, bounded replay and explicit `resync_required` semantics.
- `GET /api/v1/events` Server-Sent Events endpoint plus React EventSource → TanStack Query invalidation bridge.
- Complete normal inventory operator workflow: create spool, correct mass, change empty-spool mass, assign/move/unassign, archive and inspect history.
- Atomic/idempotent inventory adjustment persistence for concurrency/restart safety.
- Versioned configuration/SQLite persistence migrations with backup, validation and centralized schema ownership.
- `SecretStore` boundary separating Bambu access codes and Moonraker API keys from ordinary runtime configuration.
- Optional independent SHA-256 certificate pins for Bambu MQTT and FTPS.
- Hardened Moonraker endpoint policy covering resolved destinations, unsafe mixed DNS results, redirects and URL userinfo.
- Artifact quota/minimum-free-space controls, safe orphan retention/cleanup and restart cleanup.
- Per-printer reconnect supervision with bounded global concurrency and independent backoff/jitter.
- Production-container Playwright acceptance across desktop, tablet and mobile for printer setup, queue staging/start, realtime resync and representative inventory operations.
- Machine-checkable physical/deployment evidence manifests for AUD-003, AUD-013 and the P3 resume gate.

### Safety and governance

- Job-control side effects are non-retryable when the remote outcome is ambiguous; same-key unresolved replay never sends the command again.
- Realtime continuity fails closed to canonical HTTP resynchronization on malformed, foreign, expired or overflowed cursors.
- Queue/inventory realtime notifications publish only after durable writes succeed.
- Browser operator credentials remain memory-only; production rejects tokenless `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true`.
- Frozen npm/pip dependency inputs, Dependabot, dependency audits, final-image HIGH/CRITICAL scanning and branch-aware backend coverage governance are in place.
- Backend measured branch-aware coverage is approximately 76% with a 75% CI floor.

### Deployment

- Backend package version: `0.1.0a4`.
- Frontend/application version: `0.1.0-alpha.4`.
- Frozen release commit: `457f8f3f044147772b1ecf13df90b38a35268cda`.
- Versioned image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.4`.
- Published multi-architecture digest: `sha256:0b0d96e5243db82ad3349bbc1c96243cbc6288c27eb716ff80512eb925b9fef4`.
- Linux `amd64` and `arm64` are published with SBOM/provenance metadata.
- The companion Umbrel package line pins the exact immutable digest and maps Umbrel `APP_PASSWORD` to `FOXFORGE_COMMAND_TOKEN` for explicit memory-only **Unlock writes** while keeping App Proxy as defense in depth.

### Validation

- Guarded release workflow passed on the exact frozen release commit before publication.
- Release validation passed manifest/version consistency, frozen dependency installation, Ruff lint/format, **269 backend tests**, TypeScript typecheck, **42 frontend tests**, Vite production build and unified release-image health/SPA/persistence smoke.
- Linux `amd64` + `arm64` publication completed with SBOM/provenance before the GitHub pre-release was created.
- Companion Umbrel package CI validates the exact digest, Compose/auth bootstrap contract, anonymous image pull and runtime startup on both `amd64` and `arm64`.

### Known limitations

- Physical Bambu X2D validation remains required for connection/reconnect, state sync, MQTT/FTPS certificate behavior, project delivery, print-start acknowledgement, Pause/Resume/Cancel, lifecycle completion and ambiguous-outcome reconciliation.
- Physical Moonraker/OpenKE validation remains required for endpoint-policy compatibility, HTTP/WebSocket behavior, upload/checksum/start, Pause/Resume/Cancel and lifecycle completion/failure handling.
- Representative Raspberry Pi 5/UmbrelOS installation, restart/persistence, real proxy/write path, direct-backend fail-closed behavior, printer-network reachability, upgrade and SSE reconnect/resync validation remains incomplete.
- Automatic filament accounting P3 is **not included**; the partial implementation remains frozen in draft PR #58 behind the physical/deployment validation gate.
- Persistent farm scheduling/distributed leases are not implemented.
- Deep Bambu AMS/CFS operations, drying, HMS actions, K profiles, dual-nozzle controls and other vendor-depth capabilities remain future typed work.
- Persistence compatibility remains pre-stable; back up the complete sensitive `/data` directory before upgrades.

## [0.1.0-alpha.3] - 2026-09-04

Third public FoxForge pre-release. `alpha.3` moves the previously read-mostly web application to a guarded, authenticated management workflow for printer configuration, filament inventory and print submission while preserving strict queue-safety and vendor-isolation contracts. See [`release/v0.1.0-alpha.3.md`](release/v0.1.0-alpha.3.md) for the full release notes.

### Added

- Application-level command security boundary with fail-closed authentication, explicit principal permissions, request correlation, durable HTTP idempotency, normalized errors and append-only SQLite command audit.
- Browser operator-session support for trusted self-hosted command workflows without relying on Umbrel App Proxy as the sole authorization layer.
- Authenticated printer setup API and UI for add, update, remove, connectivity test and reconnect operations while keeping stored credentials out of public read models.
- Authenticated/idempotent inventory mutations for spool creation, mass correction, empty-spool mass changes, assignment/move/unassign and archival.
- Restart-safe content-addressed `.gcode` / `.3mf` staging under `/data/artifacts` with SHA-256 verification and bounded uploads.
- Authenticated/idempotent queue enqueue, explicit dispatch and explicit reconciliation endpoints.
- Safe browser print workflow: select a local file, hash it in the browser, upload file bytes, enqueue the verified artifact and then explicitly start the print.
- EN/RU/UK copy and localization parity coverage for the new command workflows.

### Changed

- Durable queue `dispatch_id` is now explicitly separate from the per-command HTTP `Idempotency-Key`.
- An uncertain replay preserves the same HTTP idempotency key; a conclusively blocked attempt may later be intentionally reassessed with a fresh HTTP key while retaining the same queue dispatch identity.
- Retry controls are exposed only for backend-confirmed retryable, receipt-free pre-start failures.
- The Add Printer control is now connected to the actual printer setup workflow rather than remaining disabled.
- The Umbrel package documentation now describes UI-based printer setup, durable `/data/artifacts` staging and the explicit enqueue/start/reconcile workflow.

### Safety

- `INDETERMINATE` remains reconciliation-only. FoxForge does not offer a blind retry after an ambiguous remote printer side effect.
- Receipt-bearing queue entries are never blindly redispatched.
- No public route accepts an arbitrary server-side filesystem path for a print job; browser-selected client paths are not transmitted as server paths.
- Artifact identity is based on verified SHA-256 content rather than a client filename/path.
- Raw bearer tokens and raw HTTP idempotency keys are not persisted in command audit records.
- `alpha.3` still does not expose a generic unrestricted printer-command endpoint.

### Deployment

- Backend package version: `0.1.0a3`.
- Frontend/application version: `0.1.0-alpha.3`.
- Frozen release commit: `1a2ec61ae1a3766e7266449658524ea2e5de6647`.
- Versioned image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.3`.
- Published multi-architecture digest: `sha256:efab08cdbfa515d83b665a71c2b48642d530c4880ec0d7b85b5488a34e2acc94`.
- Linux `amd64` and `arm64` images are published with SBOM/provenance metadata.
- Companion Umbrel Community App was updated through `MikeFox303/umbrel-3d-printing-store` PR #24 and merged as `d0476106ff43bcab98f9b73d0286a5c3d24c4e95`, pinned to the immutable multi-architecture digest above.

### Validation

- Guarded release workflow passed on the exact frozen release commit before tag/pre-release creation.
- Release validation passed manifest/version consistency, backend installation, Ruff lint, Ruff formatting, **171 backend tests**, frontend installation, TypeScript typecheck, **28 frontend tests**, Vite production build and unified container smoke checks.
- Unified release-image smoke verified `/healthz`, SPA serving, first-start config creation and SQLite persistence.
- Linux `amd64` + `arm64` image publication completed successfully before the Git tag and GitHub pre-release were created.
- PR #51 safe browser queue workflow was additionally validated after merge on `main` with frontend typecheck/tests/build, unified container smoke and multi-architecture publication.
- Umbrel Store PR #24 passed its package contract and Compose checks, Upstream Version Audit, and anonymous public runtime smoke tests on both `linux/amd64` and `linux/arm64`.
- The post-merge FoxForge Umbrel Package workflow repeated package/Compose validation plus anonymous `amd64` and `arm64` runtime smoke successfully on Store `main` commit `d0476106ff43bcab98f9b73d0286a5c3d24c4e95`.

### Known limitations

- Physical Bambu LAN/X2D validation is still required for connection/reconnect, project delivery, print-start acknowledgement, lifecycle completion and ambiguous-start reconciliation on representative hardware.
- Physical Moonraker/OpenKE validation is still required for HTTP/WebSocket connectivity, upload/start and lifecycle completion/failure behavior.
- Representative Raspberry Pi 5/UmbrelOS printer-network, restart, persistence and upgrade validation remains incomplete even though ARM64 images and the Umbrel package are exercised in CI/QEMU.
- Common Pause / Resume / Cancel controls are intentionally not included in `alpha.3`.
- Realtime WebSocket/SSE application-event delivery is not implemented; the web UI continues to poll.
- Automatic queue-to-filament consumption accounting is not implemented.
- Inventory command APIs exist, but the full inventory mutation UI is not yet complete.
- Persistent farm scheduling/distributed lease semantics are not implemented.
- Deep Bambu AMS operations/drying, HMS actions, K profiles, dual-nozzle controls and validated X2D-specific storage behavior remain future typed capabilities.
- Persistence compatibility is still pre-stable; back up `/data` before upgrading between early alpha builds.

## [0.1.0-alpha.2] - 2026-09-04

Second public FoxForge pre-release. `alpha.2` made the runnable alpha substantially more truthful and deployable: live runtime failures, empty states, inventory state and printer telemetry became explicit, and the first immutable Umbrel Community App package was published. See [`release/v0.1.0-alpha.2.md`](release/v0.1.0-alpha.2.md) for release-specific notes.

### Added

- Explicit live-runtime UI states for initial loading, ready operation, background refresh and recoverable API failure, including retry actions and aligned EN/RU/UK copy.
- Healthy first-run empty states for unconfigured printer, queue and material-system workspaces instead of misleading zero/error presentation.
- Independent Inventory loading/error/retry/refresh presentation plus a true-empty inventory state distinct from a filter with no matches.
- Printer telemetry phases distinguishing live, stale, connecting, degraded and unavailable data.
- Honest System runtime/API status instead of an unconditional UI + API healthy claim.
- ADR 0003 and upstream-adoption guardrails defining Bambuddy as the primary Bambu protocol/behavior reference, PrintBuddy as the provider-isolation reference and PrintOps as the farm/operations reference.
- First FoxForge package in `MikeFox303/umbrel-3d-printing-store` as `my3d-foxforge`, using authenticated Umbrel App Proxy, persistent `/data` and immutable release-image pinning.

### Changed

- `/api/v1/fleet` and `/api/v1/queue` use independent frontend request lifecycles so one endpoint failure no longer erases successful sibling data.
- Stale, degraded, disconnected, connecting and offline printer telemetry can no longer be rendered as healthy live state.
- Runtime, inventory and printer-state presentation remains localized and key-parity tested across English, Russian and Ukrainian.
- Documentation distinguishes CI/QEMU ARM64 validation from representative Raspberry Pi 5 hardware validation.

### Deployment

- Backend package version: `0.1.0a2`.
- Frontend/application version: `0.1.0-alpha.2`.
- Versioned image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.2`.
- Guarded release workflow published Linux `amd64` + `arm64` and created the GitHub pre-release after backend, frontend and unified-container validation.
- Companion Umbrel package was pinned to the resulting immutable multi-architecture digest and independently smoke-tested.

### Safety

- Public HTTP write APIs were intentionally not yet exposed in `alpha.2`.
- `INDETERMINATE` print starts remained non-retryable without reconciliation, and receipt-bearing jobs were never blindly redispatched.
- Inventory retained ownership of FoxForge spool identity; printer material snapshots exposed physical material state and opaque slot IDs rather than inventory `spool_id` values.
- Common application/domain code remained independent of Bambu and Moonraker transport types while deep Bambu features remained vendor-specific typed capabilities.

### Validation

- PR #29 merged live API runtime feedback.
- PR #31 merged healthy empty alpha runtime states.
- PR #32 merged independent Inventory runtime feedback.
- PR #35 merged truthful printer telemetry presentation.
- PR #36 merged truthful System API/runtime status.
- PR #37 merged independent Fleet/Queue read lifecycles after Web UI typecheck/tests/build and unified-container smoke passed on the exact PR head.
- The guarded `alpha.2` release workflow completed successfully before the release tag/image/pre-release were published.

### Known limitations

- Physical Bambu LAN/X2D, Moonraker/OpenKE and representative Raspberry Pi 5/UmbrelOS validation remained pending.
- Printer configuration was still file-based in the shipped `alpha.2` release.
- Realtime WebSocket/SSE delivery, automatic filament accounting, persistent farm scheduling and deep Bambu AMS/HMS/K-profile/dual-nozzle controls remained future work.

## [0.1.0-alpha.1] - 2026-09-04

First public runnable FoxForge pre-release. It introduced the unified backend + React runtime, Bambu and Moonraker adapter foundations, durable queue and inventory, read-only `/api/v1`, EN/RU/UK localization, Docker packaging and guarded Linux `amd64`/`arm64` publication. See [`release/v0.1.0-alpha.1.md`](release/v0.1.0-alpha.1.md) for release-specific notes.

### Foundation delivered before and through alpha.1

- ADR 0001 vendor-independent `PrinterAdapter` architecture with typed capability discovery.
- Bambu adapter, LAN MQTT/FTPS transport and Bambu-specific project-storage strategy boundary.
- Moonraker/Klipper adapter and production HTTP/WebSocket transport.
- `FleetService`, durable queue state machine, explicit `INDETERMINATE` reconciliation semantics and restart-safe SQLite queue persistence.
- Event-driven queue lifecycle tracking and safe retry policy for retryable receipt-free pre-start failures.
- Independent inventory bounded context with exact `Decimal` mass accounting, immutable adjustment history, slot assignments and SQLite persistence.
- Repository layout split into `backend/`, `frontend/` and `deployment/` ownership boundaries under ADR 0002.
- Unified self-hosted Docker runtime and EN/RU/UK React interface.

## Historical development record

The earlier changelog contained a commit-by-commit implementation log covering the initial printer-domain foundation, Bambu/Moonraker adapter phases, queue lifecycle/retry phases, inventory foundation/SQLite persistence and repository-layout migration. Git remains the canonical source for that history, while durable architecture and design rationale is retained in the repository ADRs and `docs/design/` documents.

Key pre-release milestones include:

- Phase 1 Printer domain foundation — PR #2, squash commit `3150a2f08cdf490636a5ddcc22392e7c2aab6c9b`.
- Bambu adapter foundation — PR #3, squash commit `e5568affd7af3d72f6020f2734c9f7c448ff1a26`.
- AdapterRegistry/FleetService — PR #4, squash commit `ad2b97008ddaaf4edd506a8a79deae2eb8c89544`.
- Durable queue dispatch — PR #5, squash commit `7cfcd57a0a83f7138a8b47454abba82770f51139`.
- Moonraker adapter foundation — PR #6, squash commit `10aa2f5dfa21d46f1eb0b0691caf9814fedc0f4e`.
- Moonraker HTTP/WebSocket transport — PR #7, squash commit `5ae2a361000ed2864098cb0ca940bf96184fc752`.
- Bambu LAN transport — PR #8, squash commit `9e02cbbe2c4461ababf6de342b35f4a8ac5c558f`.
- Bambu project-storage separation — PR #9, squash commit `05522b5c3b8c99676eaa7adda59659261d115bea`.
- Queue event lifecycle and retirement of the temporary port-6000 experiment — PR #11, squash commit `0fde0c7da472f29764b1ca37822e934f983015f4`.
- Safe queue retry runner — PR #12, squash commit `6cb3332cc20d9a7ddfb416077c73d0ebba0cb61e`.
- Inventory foundation — PR #13, squash commit `eeacb8fcd12f704b0d97d1dce02874f12d103a2d`.
- ADR 0002 repository-layout migration — PR #14, squash commit `294ebc652504dc488a35740ff92c6c98ad20d0df`.
- Durable SQLite inventory — PR #18, squash commit `5f150b130679e572e057da3210f28b6ccad1f8ec`.

The temporary X2D/N6 port-6000 experiment remains only in Git history. Any future X2D/eMMC implementation must be newly validated behind the production `BambuProjectStorage` boundary rather than promoting the retired experimental code.
