# Changelog

All notable FoxForge changes are recorded here. The Git repository remains the canonical project history; this file summarizes user-visible, release and architectural milestones rather than every intermediate commit.

FoxForge has not published a stable release yet. Alpha releases are versioned below; the detailed development log is retained afterward as historical implementation context. Historical entries may describe intermediate states that were superseded by later sections.

## Unreleased

### Added

- Authenticated, idempotent queue commands for enqueue, dispatch and explicit uncertain-outcome reconciliation using the existing durable queue safety model.
- Restart-safe SHA-256 content-addressed `.gcode`/`.3mf` artifact staging without accepting client-supplied server filesystem paths.
- Append-only SQLite command audit covering current authenticated mutation routes without storing bearer tokens or raw idempotency keys.
- Single-process queue command serialization preventing concurrent HTTP dispatch/reconcile calls from racing the durable `DISPATCHING` boundary.
- Queue command/artifact design documentation and tests for replay, `INDETERMINATE`, reconciliation, artifact integrity/restart behavior and audit persistence.

### Validation

- Ruff lint and format pass on Python 3.12 and 3.13.
- Full backend suite passes with 171 tests at the queue-command merge gate.
- Unified FoxForge container build/start/health/UI smoke validation passes with artifact, queue-command and audit composition enabled.

### Known limitations

- Queue upload/dispatch controls are not yet integrated into the React UI.
- Physical X2D and Moonraker/OpenKE upload/start/reconciliation validation remains pending.
- The queue HTTP lock is a single-process safety boundary; multi-process/distributed runners still require durable lease/CAS semantics.

## [0.1.0-alpha.2] - 2026-09-04

### Added

- Explicit live-runtime UI states for initial loading, ready operation, background refresh and recoverable API failure, including retry actions and aligned EN/RU/UK copy.
- Healthy first-run empty states for unconfigured printer, queue and material-system workspaces instead of misleading zero/error presentation.
- Independent Inventory loading/error/retry/refresh presentation plus a true-empty inventory state distinct from a filter with no matches.
- Printer telemetry phases that distinguish live, stale, connecting, degraded and unavailable data in the printer cockpit.
- Honest System runtime/API status instead of an unconditional UI + API healthy claim.
- ADR 0003, upstream adoption guidance and repository guardrails defining Bambuddy as the primary Bambu protocol/behavior reference, PrintBuddy as the provider-isolation reference and PrintOps as the farm/operations reference.
- First FoxForge package in `MikeFox303/umbrel-3d-printing-store` as `my3d-foxforge`, using authenticated Umbrel App Proxy, persistent `/data` and immutable release-image pinning.

### Changed

- `/api/v1/fleet` and `/api/v1/queue` are now polled through independent frontend request lifecycles. An endpoint-specific failure no longer erases successful sibling data, while the combined runtime still surfaces an explicit error and retry path.
- Stale, degraded, disconnected, connecting and offline printer telemetry can no longer be rendered as healthy live state.
- Runtime, inventory and printer-state presentation remains localized and key-parity tested across English, Russian and Ukrainian.
- Current `main` documentation records the Community App deployment and distinguishes CI/QEMU ARM64 validation from still-pending representative Raspberry Pi 5 hardware validation.

### Deployment

- Backend package version: `0.1.0a2`.
- Frontend/application version: `0.1.0-alpha.2`.
- Versioned image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.2`.
- The guarded release workflow validates backend, frontend and the unified container before publishing Linux `amd64` + `arm64` and creating the GitHub pre-release.
- The companion Umbrel Store is updated only after publication, using the resulting immutable multi-architecture digest and separate anonymous amd64/arm64 runtime smoke tests.

### Safety

- The public HTTP API remains read-only; `alpha.2` does not introduce anonymous printer-control, queue-mutation, inventory-mutation or remote-configuration endpoints.
- `INDETERMINATE` print starts remain non-retryable without reconciliation, and receipt-bearing jobs are never blindly redispatched.
- Inventory still owns FoxForge spool identity; printer material snapshots continue to expose physical material state and opaque slot IDs rather than `spool_id` values.
- Common application/domain code remains independent of Bambu and Moonraker transport types, while deep Bambu features remain vendor-specific typed capabilities.

### Validation

- PR #29 merged live API runtime feedback.
- PR #31 merged healthy empty alpha runtime states.
- PR #32 merged independent Inventory runtime feedback.
- PR #35 merged truthful printer telemetry presentation.
- PR #36 merged truthful System API/runtime status.
- PR #37 merged independent Fleet/Queue read lifecycles after Web UI typecheck/tests/build and unified-container smoke passed on the exact PR head.
- The `alpha.2` release candidate remains subject to the guarded release workflow before the tag/image/pre-release are created.

### Known limitations

- Physical Bambu LAN/X2D validation remains pending for connection/reconnect, FTPS delivery, print start, lifecycle completion and X2D-specific storage behavior.
- Physical Moonraker/OpenKE validation remains pending for HTTP/WebSocket connectivity, upload/start and lifecycle completion.
- Representative Raspberry Pi 5/UmbrelOS hardware validation remains pending even though ARM64 execution is exercised in CI.
- Printer configuration remains file-based; authenticated web configuration is not implemented.
- Realtime WebSocket/SSE delivery, automatic filament accounting, persistent farm scheduling and deep Bambu AMS/HMS/K-profile/dual-nozzle controls remain future work.

## [0.1.0-alpha.1] - 2026-09-04

First public runnable FoxForge pre-release. It introduced the unified backend + React runtime, Bambu and Moonraker adapter foundations, durable queue and inventory, read-only `/api/v1`, EN/RU/UK localization, Docker packaging and guarded Linux `amd64`/`arm64` publication. See [`release/v0.1.0-alpha.1.md`](release/v0.1.0-alpha.1.md) for release-specific notes.

## Detailed development log

The entries below are retained from the pre-versioned and early-alpha implementation log. They document the sequence of architecture and implementation work and can describe intermediate states later superseded by the versioned sections above.

### Added

- Responsive live-runtime feedback for initial API connection, background refresh and recoverable API failures, with an explicit retry action and EN/RU/UK copy instead of silently rendering an empty fleet.
- Bambu adapter foundation under `foxforge.adapters.bambu`.
- Bambu-native transport protocol and DTO boundary so vendor-specific MQTT/storage details remain outside the common printer domain.
- Anti-corruption mappings from Bambu printer states, job progress, faults and material systems into FoxForge normalized printer contracts.
- Bambu `PrintExecutionCapability` translating common plate selection and opaque material bindings into Bambu-native print requests.
- Bambu `MaterialSystemCapability` exposing AMS-family devices as normalized material units and slots while preserving opaque vendor routing internally.
- Normalized Bambu transport error mapping, including explicit `INDETERMINATE` outcomes.
- Bambu lifecycle/event pump with reconnect epochs and normalized connection, printer-state, job-progress and material-system events.
- Bambu adapter architecture/provenance documentation and architecture tests that prevent direct dependencies on Bambuddy backend code or historical integration records.
- Package-qualified test layout and reusable test helpers to avoid nested `conftest.py` and duplicate-module-name collection collisions.
- Vendor-neutral `AdapterRegistry` that maps persisted `adapter_kind` values to composition-root factories without importing concrete vendor adapters.
- Application-level `FleetService` for normalized identity/snapshot/capability lookup, printer lifecycle operations and merged printer event delivery.
- Mixed-fleet tests proving `FakePrinterAdapter` and `BambuAdapter` can coexist behind the same fleet service.
- Architecture tests preventing the application layer and generic adapter registry from importing Bambu, Moonraker or concrete adapter packages.
- Application-level `QueueService` routing automated dispatch exclusively through `FleetService` and common `PrintExecutionCapability`.
- Persisted queue state machine with `PENDING`, `BLOCKED`, `DISPATCHING`, `ACCEPTED`, `INDETERMINATE`, and `FAILED` dispatch states.
- Durable queue-owned `dispatch_id`, assessment, receipt/error, dispatch-attempt metadata, and explicit reconciliation API.
- `InMemoryQueueStore` for deterministic tests and `SQLiteQueueStore` for durable single-container Docker/ARM64/Umbrel deployments.
- Restart tests proving accepted queue entries cannot start a second print after a new store/adapter instance and uncertain entries cannot be blindly retried.
- Queue dispatch design documenting the pre-submit crash boundary and reconciliation semantics.
- Moonraker/Klipper adapter foundation under `foxforge.adapters.moonraker`.
- Moonraker-native state/print DTO boundary keeping Klipper/Moonraker fields out of the common printer domain.
- Moonraker transport protocol and normalized transport error kinds for connection, live state and print submission.
- Moonraker anti-corruption mapping for Klippy readiness, `print_stats` state/progress, faults and normalized printer/job snapshots.
- Moonraker `PrintExecutionCapability` for verified local G-code artifacts with explicit rejection of unsupported plate selection.
- Moonraker `MaterialSystemCapability` exposing one stable external-spool slot without fabricating AMS/CFS semantics.
- Moonraker lifecycle/event pump with reconnect epochs and normalized connection, printer-state, job-state, progress and material-system events.
- Mixed real-adapter fleet test proving Bambu and Moonraker can coexist behind the same `FleetService` and common capabilities.
- Cross-vendor architecture guards preventing Bambu and Moonraker adapter packages from importing each other or historical Bambuddy integration modules.
- Moonraker adapter design/provenance documentation.
- Production `MoonrakerHttpTransport` using one `aiohttp` stack for HTTP multipart/file-control requests and WebSocket status subscriptions.
- Moonraker API-key authentication through `X-Api-Key`, initial `/printer/info` reconciliation, and `printer.objects.subscribe` live updates for `webhooks`, `print_stats`, and `virtual_sdcard`.
- G-code upload to Moonraker's `gcodes` root with SHA-256 checksum and explicit print start after a confirmed upload.
- Fail-safe print-start error semantics that surface post-request timeout/network ambiguity as `INDETERMINATE` instead of permitting an automatic duplicate start.
- Local fake Moonraker HTTP/WebSocket server tests covering authentication, subscription updates, multipart checksum upload/start, and indeterminate start timeout.
- Registry-ready `create_moonraker_http_adapter()` production factory so concrete Moonraker wiring remains a composition-root concern rather than a branch inside `AdapterRegistry`.
- Moonraker HTTP/WebSocket transport design documenting wire semantics, safety boundaries, test coverage, and the remaining physical-printer validation gate.
- Phase 7 Bambu LAN transport with MQTT 3.1.1 over TLS, QoS-1 request publishing, implicit-FTPS file delivery, and `create_bambu_lan_adapter()` composition factory.
- Sticky Bambu LAN codec that merges incremental `push_status` reports and retains AMS/AMS 2 Pro/AMS HT typing discovered through `get_version`.
- Bambu LAN print-start sequence with mandatory busy checks both before file upload and immediately before `project_file` dispatch.
- Size-aware implicit-FTPS uploads using manual `STOR` data transfer plus `226`/remote-`SIZE` confirmation so a known partial 3MF cannot proceed to print start.
- Bambu LAN safety tests covering sticky AMS state, plate/material routing, pre-upload busy rejection, upload-race busy rejection, ambiguous MQTT start handling, FTPS confirmation recovery, and partial-file rejection.
- Bambu LAN production-transport design/provenance documentation with an explicit X2D/N6 hardware-validation boundary.
- Phase 8 Bambu-specific `BambuProjectStorage` strategy boundary separating project delivery from MQTT print control without changing common Queue/Fleet contracts.
- `BambuStoredProject` value model carrying validated remote filename, Bambu-native project URL, and storage kind for standard FTPS or future validated internal-eMMC delivery.
- `FtpsBambuProjectStorage` preserving the merged Phase 7 implicit-FTPS behavior as the default production storage strategy.
- Project-storage tests proving `BambuLanTransport` can forward a storage-owned `brtc://emmc/...` project reference without any alternate uploader being imported into production.
- Bambu project-storage design documenting the future X2D/eMMC extension point and its physical-validation gate.
- Phase 9 queue lifecycle states `PREPARING`, `PRINTING`, `PAUSED`, `COMPLETED`, and `CANCELLED` above the durable accepted dispatch state.
- Event-driven queue tracking from normalized `FleetService` `JOB_STATE_CHANGED` events with strict confirmed `vendor_job_id` matching.
- `QueueService.start()` startup reconciliation so restored accepted/running entries can resume lifecycle tracking from the current normalized printer snapshot.
- Terminal-state replay protection so completed, failed, or cancelled queue entries cannot regress from stale later events.
- SQLite lifecycle test proving a completed remote job and its original dispatch receipt survive a store/process restart.
- Queue event-lifecycle design documenting identity matching, restart reconciliation, replay safety, and the rule that `INDETERMINATE` is never auto-resolved.
- Phase 10 `QueueRetryPolicy` with configurable initial delay, exponential multiplier, capped delay, and maximum attempt count.
- Phase 10 `QueueRunner.run_once()` deterministic scheduling pass for pending/blocked entries and safe retryable pre-start failures.
- Queue-runner protection that never retries `DISPATCHING`, `INDETERMINATE`, non-retryable failures, exhausted failures, or any receipt-bearing remote job.
- One-entry-per-printer processing per runner pass plus serialization of concurrent `run_once()` calls inside one runner instance.
- Queue retry tests covering backoff deadlines, stable `dispatch_id`, maximum attempts, blocked reassessment, `INDETERMINATE`, remote failed jobs, and concurrent runner calls.
- Queue retry/single-pass runner design documenting the current single-container concurrency boundary and future scheduler requirements.
- Phase 11 independent `domain.inventory` bounded context for spool metadata, mass accounting, archive state and physical slot assignment.
- Phase 11 `InventoryService` and `InventoryStore` application boundary with deterministic `InMemoryInventoryStore` contract implementation.
- Immutable spool-adjustment ledger using `Decimal` mass accounting for consumption, waste, returns and manual corrections.
- Per-adjustment idempotency keys with conflicting-replay detection and exactly-once replay semantics that remain valid after a spool is later archived.
- Inventory-owned `(printer_id, slot_id) -> spool_id` assignment state while keeping `spool_id` out of `MaterialSystemCapability` and printer adapter snapshots.
- Editable empty-spool mass, purchase date, manufacturer/product/color metadata, archive rules and remaining/used filament balance calculation.
- Inventory contract tests covering balance limits, correction audit history, idempotency, archive behavior, assignment conflicts and movement between multi-slot/external material sources.
- Inventory foundation design documenting backend/UI coordination, the future API read-model boundary and the next durable SQLite slice.
- Phase 12 `SQLiteInventoryStore` implementing the existing `InventoryStore` port under `backend/src/foxforge/infrastructure/inventory`.
- Versioned SQLite persistence for spool metadata, append-only adjustments and physical slot assignments with exact `Decimal`-as-string serialization.
- Database-level unique adjustment idempotency keys, spool/slot uniqueness, foreign keys, WAL mode and a five-second busy timeout for the current single-container runtime.
- SQLite restart tests proving spool metadata, editable empty-spool weight, ledger balance, archived adjustment replay and physical slot assignments survive store/process recreation.
- Inventory infrastructure architecture guard preventing printer or vendor dependencies from leaking into persistence code.
- Phase 12 design documenting persistence schema, restart/idempotency guarantees, backend/frontend isolation and the future public API boundary.

### Changed

- Material system freshness is explicitly observable across Bambu disconnect/reconnect through normalized `material_system_changed` events.
- Confirmed Bambu dispatch receipts are idempotently cached by `dispatch_id`; indeterminate starts remain unreconciled until the queue/application layer resolves them.
- Fleet event relays subscribe before fleet-managed connect operations, so connection/reconciliation events are not lost during startup.
- Queue dispatch persists `DISPATCHING` before invoking the adapter side effect; a process restart from that state requires reconciliation rather than an automatic retry.
- Confirmed queue receipts are now retained through preparing, printing, pause/resume, completion, cancellation and remotely observed failure for future accounting/reconciliation.
- `FAILED` queue entries may now retain a receipt when the confirmed remote print failed; pre/at-dispatch failures still have no receipt.
- Queue lifecycle correlation never guesses by filename or printer alone; entries without a confirmed `vendor_job_id` remain at the last safely known state.
- Safe automatic retry is now limited to receipt-free `FAILED` entries whose normalized error explicitly sets `retryable=True`; the retry uses the original durable `dispatch_id`.
- `BLOCKED` entries may be reassessed by the runner without incrementing `attempt_count`; attempts are counted only after QueueService persists the `DISPATCHING` boundary.
- Inventory mass history is append-only: manual fixes create `CORRECTION` adjustments instead of rewriting prior consumption records.
- Inventory assignment treats `slot_id` as opaque and vendor-independent; AMS/CFS/external-spool semantics remain in printer capabilities rather than inventory production code.
- Phase 11 intentionally does not modify `frontend/`, `README.md` or `docs/README.md`, allowing the parallel web-interface PR to continue without backend/UI file conflicts. Future HTTP DTOs will adapt `InventoryService` read models rather than making current frontend mock types authoritative.
- Repository layout now follows ADR 0002: Python runtime code/tests/packaging live under `backend/`, the web UI owns `frontend/`, and Docker/Umbrel packaging belongs under `deployment/`.
- Phase 12 follows the `backend/` ownership boundary and leaves `frontend/` untouched while the web-interface stream develops in parallel.
- CI now prints the exact Ruff formatter diff when formatting validation fails.
- Runtime dependencies now include `aiohttp>=3.12,<4` for Moonraker HTTP/WebSocket transport support and `paho-mqtt>=2.1,<3` for Bambu LAN MQTT support.
- Bambu FTPS whole-transfer deadlines are derived from file size and a pessimistic transfer floor rather than reusing the short MQTT command timeout.
- `BambuLanTransport` now consumes a Bambu-specific project-storage strategy; `project_file.url` comes from the storage result instead of being hard-coded to FTP inside the MQTT codec.
- The default Bambu production composition remains standard implicit FTPS; there is no automatic model detection or hidden alternate-storage fallback.
- The former `integrations/bambuddy/x2d_port6000/` experiment and `.github/workflows/bambuddy-port6000-validation.yml` were removed after review showed the sidecar design violated the FoxForge adapter boundary and carried unresolved upstream-source/provenance risk.
- Root project documentation now points implementation commands at `backend/` and describes the repository as a multi-component application rather than a Python-only root package.

### Removed

- Direct Bambuddy backend package imports from FoxForge production code.
- The experimental X2D port-6000 sidecar from the active implementation path.

### Fixed

- Bambu busy-state checks now happen again after project upload and immediately before MQTT print dispatch.
- Partial or unconfirmed Bambu FTPS uploads no longer proceed into print start.
- Bambu FTPS reply-time recovery now attempts one guarded metadata verification; known size mismatch remains a hard failure.
- Moonraker post-start acknowledgement timeouts remain explicit `INDETERMINATE` outcomes rather than retryable transport failures.
