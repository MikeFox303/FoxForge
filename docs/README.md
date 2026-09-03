# FoxForge documentation

FoxForge treats the Git repository as the canonical source for durable architecture and design decisions.

## Architecture Decision Records

- [ADR 0001: PrinterAdapter architecture](adr/0001-printer-adapter-architecture.md) — accepted. Defines the vendor-independent printer boundary, typed capability model, and migration sequence for deep Bambu plus multi-vendor support.

## Design specifications

- [Printer contracts v1](design/printer-contracts.md) — normative design for `PrinterAdapter`, `PrintExecutionCapability`, `MaterialSystemCapability`, normalized events/errors, idempotency semantics, and required contract tests.
- [Bambu adapter foundation](design/bambu-adapter-foundation.md) — implementation boundary and provenance for the first Bambu anti-corruption adapter slice, including native-state mapping, common capabilities, and transport separation.
- [Bambu LAN production transport](design/bambu-lan-transport.md) — Phase 7 MQTT/TLS plus Bambu project-storage delivery, sticky Bambu-native state, double busy guards, verified upload semantics, indeterminate start handling, and hardware-validation boundaries.
- [Bambu project storage strategy](design/bambu-project-storage.md) — Phase 8 Bambu-specific storage seam separating MQTT print control from FTPS or future validated internal-eMMC delivery without changing common queue/fleet contracts.
- [AdapterRegistry and FleetService](design/fleet-service.md) — Phase 3 composition/application boundary for vendor-neutral adapter creation, fleet snapshots/capabilities, lifecycle, and merged normalized events.
- [Queue dispatch and durable idempotency](design/queue-dispatch.md) — Phase 4 queue state machine, persisted dispatch crash boundary, reconciliation semantics, and SQLite restart durability.
- [Queue event-driven print lifecycle](design/queue-event-lifecycle.md) — Phase 9 normalized remote-job tracking from accepted dispatch through preparing, printing, pause/resume and terminal states with strict vendor-job identity matching.
- [Queue retry and single-pass runner policy](design/queue-retry-policy.md) — Phase 10 safe pre-start retry/backoff rules, one-entry-per-printer passes, and explicit protection of `DISPATCHING`, `INDETERMINATE`, and receipt-bearing jobs.
- [Moonraker/Klipper adapter foundation](design/moonraker-adapter-foundation.md) — Phase 5 second real adapter family, native-state boundary, common G-code execution, and external-spool material semantics.
- [Moonraker HTTP/WebSocket transport](design/moonraker-http-transport.md) — Phase 6 production wire transport, API-key auth, state subscription, checksum upload/start semantics, fail-safe indeterminate handling, and hardware-validation boundary.

## Project history

- [`CHANGELOG.md`](../CHANGELOG.md) — notable implementation, architecture, validation, and migration milestones.

## Working rule

Architectural decisions belong in ADRs. Detailed interface contracts may live in design specifications linked from the relevant ADR. Implementation PRs should reference the ADR/design document they implement and include acceptance criteria and tests.
