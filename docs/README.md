# FoxForge documentation

FoxForge treats the Git repository as the canonical source for durable architecture and design decisions.

## Architecture Decision Records

- [ADR 0001: PrinterAdapter architecture](adr/0001-printer-adapter-architecture.md) — accepted. Defines the vendor-independent printer boundary, typed capability model, and migration sequence for deep Bambu plus multi-vendor support.

## Design specifications

- [Printer contracts v1](design/printer-contracts.md) — normative design for `PrinterAdapter`, `PrintExecutionCapability`, `MaterialSystemCapability`, normalized events/errors, idempotency semantics, and required contract tests.
- [Bambu adapter foundation](design/bambu-adapter-foundation.md) — implementation boundary and provenance for the first Bambu anti-corruption adapter slice, including native-state mapping, common capabilities, and transport separation.

## Working rule

Architectural decisions belong in ADRs. Detailed interface contracts may live in design specifications linked from the relevant ADR. Implementation PRs should reference the ADR/design document they implement and include acceptance criteria and tests.
