# Changelog

All notable FoxForge changes are recorded here. The Git repository remains the canonical project history; this file summarizes user-visible and architectural milestones rather than every intermediate commit.

FoxForge has not published a stable release yet, so development milestones are listed by date/phase until the first versioned release is cut.

## Unreleased

### Added

- Bambu adapter foundation under `foxforge.adapters.bambu`.
- Bambu-native transport protocol and DTO boundary so vendor-specific MQTT/storage details remain outside the common printer domain.
- Anti-corruption mappings from Bambu printer states, job progress, faults and material systems into FoxForge normalized printer contracts.
- Bambu `PrintExecutionCapability` translating common plate selection and opaque material bindings into Bambu-native print requests.
- Bambu `MaterialSystemCapability` exposing AMS-family devices as normalized material units and slots while preserving opaque vendor routing internally.
- Normalized Bambu transport error mapping, including explicit `INDETERMINATE` outcomes.
- Bambu lifecycle/event pump with reconnect epochs and normalized connection, printer-state, job-progress and material-system events.
- Bambu adapter architecture/provenance documentation and architecture tests that prevent direct dependencies on Bambuddy backend code or the experimental integration tree.
- Package-qualified test layout and reusable test helpers to avoid nested `conftest.py` and duplicate-module-name collection collisions.
- Vendor-neutral `AdapterRegistry` that maps persisted `adapter_kind` values to composition-root factories without importing concrete vendor adapters.
- Application-level `FleetService` for normalized identity/snapshot/capability lookup, printer lifecycle operations and merged printer event delivery.
- Mixed-fleet tests proving `FakePrinterAdapter` and `BambuAdapter` can coexist behind the same fleet service.
- Architecture tests preventing the application layer and generic adapter registry from importing Bambu, Moonraker or concrete adapter packages.
- Application-level `QueueService` routing automated dispatch exclusively through `FleetService` and common `PrintExecutionCapability`.
- Persisted queue state machine with `PENDING`, `BLOCKED`, `DISPATCHING`, `ACCEPTED`, `INDETERMINATE`, and `FAILED` states.
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
- Cross-vendor architecture guards preventing Bambu and Moonraker adapter packages from importing each other or preserved Bambuddy/X2D integration code.
- Moonraker adapter design/provenance documentation.
- Production `MoonrakerHttpTransport` using one `aiohttp` stack for HTTP multipart/file-control requests and WebSocket status subscriptions.
- Moonraker API-key authentication through `X-Api-Key`, initial `/printer/info` reconciliation, and `printer.objects.subscribe` live updates for `webhooks`, `print_stats`, and `virtual_sdcard`.
- G-code upload to Moonraker's `gcodes` root with SHA-256 checksum and explicit print start after a confirmed upload.
- Fail-safe print-start error semantics that surface post-request timeout/network ambiguity as `INDETERMINATE` instead of permitting an automatic duplicate start.
- Local fake Moonraker HTTP/WebSocket server tests covering authentication, subscription updates, multipart checksum upload/start, and indeterminate start timeout.

### Changed

- Material system freshness is explicitly observable across Bambu disconnect/reconnect through normalized `material_system_changed` events.
- Confirmed Bambu dispatch receipts are idempotently cached by `dispatch_id`; indeterminate starts remain unreconciled until the queue/application layer resolves them.
- Fleet event relays subscribe before fleet-managed connect operations, so connection/reconciliation events are not lost during startup.
- Queue dispatch persists `DISPATCHING` before invoking the adapter side effect; a process restart from that state requires reconciliation rather than an automatic retry.
- CI now prints the exact Ruff formatter diff when formatting validation fails.
- Runtime dependencies now include `aiohttp>=3.12,<4` for Moonraker HTTP/WebSocket transport support.

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
- Phase 6 Moonraker HTTP/WebSocket transport integration tests are in progress on `feat/moonraker-http-transport`.

### Not yet connected

- No production Bambu MQTT/FTP transport has been wired into `BambuAdapter` yet.
- The preserved X2D/N6 port-6000 transport remains isolated pending hardware validation and is not imported by the production adapter package.
- Queue scheduling, automatic retry/backoff, event-driven completion tracking and inventory reservations are not yet implemented.
- Moonraker HTTP/WebSocket transport is implemented and under CI validation, but physical Ender/OpenKE connectivity and print-start validation are not yet complete.

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
- Preserved experimental X2D/N6 internal-storage port-6000 transport and its tests under `integrations/bambuddy/x2d_port6000`.
- CI validation for the migrated port-6000 transport.

### Notes

- The preserved Bambuddy-related tree is reference/integration work, not a replacement Bambuddy distribution.
- Production Umbrel deployment continues to consume official upstream Bambuddy releases separately from FoxForge development.
