# Changelog

All notable FoxForge changes are recorded here. The Git repository remains the canonical project history; this file summarizes user-visible and architectural milestones rather than every intermediate commit.

FoxForge has not published a stable release yet, so development milestones are listed by date/phase until the first versioned release is cut.

## Unreleased

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
- The former `integrations/bambuddy/x2d_port6000/` experiment and `.github/workflows/bambuddy-port6000.yml` were removed from the current tree. Future X2D/eMMC support will be newly implemented behind `BambuProjectStorage` after physical validation rather than promoting dormant experimental code.

### Validation

- Phase 2 Bambu adapter foundation merged through PR #3.
- Phase 2 squash commit: `e5568affd7af3d72f6020f2734c9f7c448ff1a26`.
- Phase 2 final PR CI passed Ruff and the full suite on Python 3.12 and Python 3.13.
- Phase 3 AdapterRegistry/FleetService merged through PR #4.
- Phase 3 squash commit: `ad2b97008ddaaf4edd506a8a79deae2eb8c89544`.
- Phase 3 final PR CI passed Ruff and the full suite on Python 3.12 and Python 3.13.
- Phase 4 durable queue dispatch merged through PR #5.
- Phase 4 squash commit: `7cfcd57a0a83f7138a8b47454abba82770f51139`.
- Phase 4 final PR CI passed Ruff lint, Ruff formatting, and the full suite on Python 3.12 and Python 3.13.
- Phase 5 Moonraker adapter foundation merged through PR #6.
- Phase 5 squash commit: `10aa2f5dfa21d46f1eb0b0691caf9814fedc0f4e`.
- Phase 5 final PR CI run `33807094777` passed Ruff lint, Ruff formatting, the full suite, mixed Bambu/Moonraker fleet tests and architecture guards on Python 3.12 and Python 3.13.
- Phase 6 Moonraker HTTP/WebSocket transport merged through PR #7.
- Phase 6 squash commit: `5ae2a361000ed2864098cb0ca940bf96184fc752`.
- Phase 6 final PR CI run `33807996066` passed Ruff lint, Ruff formatting, socket-level HTTP/WebSocket integration tests, factory tests, and the full suite on Python 3.12 and Python 3.13.
- Phase 7 Bambu LAN transport merged through PR #8.
- Phase 7 squash commit: `9e02cbbe2c4461ababf6de342b35f4a8ac5c558f`.
- Phase 7 final PR CI run `33810445079` passed Ruff lint, Ruff formatting, Bambu LAN storage/dispatch safety tests, production factory tests, architecture checks, and the full suite on Python 3.12 and Python 3.13.
- Phase 8 Bambu project-storage separation merged through PR #9.
- Phase 8 squash commit: `05522b5c3b8c99676eaa7adda59659261d115bea`.
- Phase 8 final PR CI run `33811264258` passed Ruff lint, Ruff formatting, Bambu project-storage tests, architecture checks, and the full suite on Python 3.12 and Python 3.13.
- Phase 9 queue event lifecycle and port-6000 retirement merged through PR #11.
- Phase 9 squash commit: `0fde0c7da472f29764b1ca37822e934f983015f4`.
- Phase 9 final PR CI run `33812534681` passed Ruff lint, Ruff formatting, lifecycle/restart/SQLite tests, architecture checks, and the full suite on Python 3.12 and Python 3.13.
- Phase 10 safe queue retry runner merged through PR #12.
- Phase 10 squash commit: `6cb3332cc20d9a7ddfb416077c73d0ebba0cb61e`.
- Phase 10 final PR CI run `33813103049` passed Ruff lint, Ruff formatting, retry/backoff/concurrency tests, architecture checks, and the full suite on Python 3.12 and Python 3.13.
- Phase 11 inventory foundation merged through PR #13.
- Phase 11 squash commit: `eeacb8fcd12f704b0d97d1dce02874f12d103a2d`.
- Phase 11 final PR CI run `33814461673` passed Ruff lint, Ruff formatting, inventory model/service/idempotency/assignment tests, architecture checks, and the full suite on Python 3.12 and Python 3.13.
- ADR 0002 repository-layout migration merged through PR #14.
- Repository-layout squash commit: `294ebc652504dc488a35740ff92c6c98ad20d0df`.
- Repository-layout validation run `33814488172` passed installation, Ruff lint/format and the existing pytest suite from `backend/` on Python 3.12 and Python 3.13.
- Current project-status documentation merged through PR #16 at `69ed3f2567de466799c3da626778a94289f135ba`.
- Phase 11 merge validation was corrected in changelog through PR #17 at `cc9232992ee9fee598ef9e4e8a65717b225487b6`.
- Phase 12 durable SQLite inventory merged through PR #18.
- Phase 12 squash commit: `5f150b130679e572e057da3210f28b6ccad1f8ec`.
- Phase 12 final PR CI run `33815207238` passed Ruff lint, Ruff formatting, SQLite restart/idempotency/assignment tests, architecture checks, and the full suite on Python 3.12 and Python 3.13.

### Not yet connected

- Bambu LAN MQTT/implicit-FTPS transport is merged and CI validated, but physical Bambu connectivity, storage, and print-start validation are still pending.
- X2D/N6-specific internal-eMMC storage remains a hardware-led future implementation behind `BambuProjectStorage`; the former port-6000 experiment is no longer present in the current source tree.
- A persistent scheduler/timer, farm-level printer selection, priorities/deadlines, and multi-process queue leases are not yet implemented above the deterministic single-pass runner.
- Queue-driven automatic consumption, material reservations and trustworthy per-material usage-estimate reconciliation are not yet connected to the durable inventory store.
- Public HTTP/API DTOs for inventory are not yet implemented; the parallel frontend continues to use its independent mock gateway until a stable API boundary is added.
- Moonraker HTTP/WebSocket transport is implemented and CI validated, but physical Ender/OpenKE connectivity and print-start validation are not yet complete.

## 2026-09-03 — Phase 1: Printer domain foundation

### Added

- ADR 0001 defining the vendor-independent `PrinterAdapter` architecture and typed capability model.
- Normative printer contracts for identity, snapshots, lifecycle, events, normalized errors and capability discovery.
- `PrintExecutionCapability` v1 with side-effect-free assessment, immutable local print artifacts, material bindings, dispatch receipts and explicit idempotency semantics.
- `MaterialSystemCapability` v1 with observation-first physical material units/slots and no inventory `spool_id` leakage into adapter state.
- `FakePrinterAdapter`, fake print execution and fake material-system capabilities for application and contract testing.
- Reconnect epochs and monotonic per-epoch event sequences.
- Shared contract tests covering lifecycle, fan-out subscriptions, capability discovery, print eligibility, dispatch conflicts and `INDETERMINATE` handling.
- Architecture tests preventing vendor imports inside `foxforge.domain.printers`.
- Python package/bootstrap configuration plus Ruff and pytest CI on Python 3.12 and 3.13.

### Validation

- Phase 1 merged through PR #2.
- Squash commit: `3150a2f08cdf490636a5ddcc22392e7c2aab6c9b`.
- Ruff and contract/unit tests passed on Python 3.12 and Python 3.13 before merge.

## 2026-09-03 — Repository and migration foundation

### Added

- Initial public FoxForge repository licensed `AGPL-3.0-only`.
- Project scope documentation for multi-vendor printer management, deep Bambu support, Moonraker/Klipper, filament inventory, AMS/CFS, print queues/farms and self-hosted Docker/Umbrel deployment.
- Preserved Bambuddy migration/provenance records after retiring the temporary production fork.
- Preserved Russian/Ukrainian Bambuddy localization work for possible future upstream contribution.
- A temporary experimental X2D/N6 internal-storage port-6000 transport and dedicated CI were migrated into early FoxForge history for evaluation.

### Changed

- On 2026-09-04 the temporary X2D/N6 port-6000 source and dedicated workflow were removed from the active repository tree. Git history retains the historical record, while any future X2D/eMMC transport will be newly implemented against the production `BambuProjectStorage` boundary after hardware validation.

### Notes

- The remaining Bambuddy-related tree is reference/migration/localization work, not a replacement Bambuddy distribution.
- Production Umbrel deployment continues to consume official upstream Bambuddy releases separately from FoxForge development.
