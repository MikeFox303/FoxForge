# FoxForge development instructions

The Git repository is the canonical source of FoxForge project state. Chat history, local notes and upstream repositories are research inputs, not authoritative FoxForge architecture.

Before architecture-significant implementation work, read:

1. [`docs/README.md`](docs/README.md)
2. [`docs/adr/0001-printer-adapter-architecture.md`](docs/adr/0001-printer-adapter-architecture.md)
3. [`docs/adr/0003-upstream-architecture-synthesis.md`](docs/adr/0003-upstream-architecture-synthesis.md)
4. the relevant design specification under [`docs/design/`](docs/design/)

## Architectural rules

- Keep common/domain/application code vendor-independent.
- Use a small `PrinterAdapter` plus typed capabilities; do not grow a lowest-common-denominator `GenericPrinter` API.
- Preserve deep Bambu behavior behind Bambu-specific capabilities instead of leaking Bambu concepts into Moonraker or other adapters.
- Treat Bambuddy primarily as the Bambu protocol/behavior reference, PrintBuddy primarily as a multi-vendor/provider reference, and PrintOps primarily as an operations/farm reference.
- Keep queue dispatch/idempotency semantics FoxForge-owned. Ambiguous starts remain `INDETERMINATE` and are never blindly retried.
- Keep inventory as an independent bounded context. FoxForge spool identity must not be embedded into native printer/material payloads.
- Scheduler/farm code may depend on FoxForge capabilities and persisted application state, never directly on MQTT, FTPS, Moonraker HTTP/WebSocket or vendor-native DTOs.
- Frontend generic features consume FoxForge API/capability models. Deep vendor UI belongs behind capability-aware vendor feature boundaries.
- Docker and Umbrel must package the same FoxForge application behavior.

## Upstream code and provenance

Use [`docs/design/upstream-adoption-map.md`](docs/design/upstream-adoption-map.md) when upstream work informs an implementation.

Classify the relationship as `inspired`, `derived` or `copied`.

For `derived` or `copied` material, record the upstream repository, exact commit/tag, source path, license, FoxForge destination, modifications and preserved copyright/license notices. FoxForge is `AGPL-3.0-only`; this does not remove upstream notice obligations.

## Implementation requirements

Every non-trivial implementation PR should define acceptance criteria and tests.

At minimum, verify the relevant failure boundaries:

- adapter reconnect and normalized errors;
- queue duplicate/ambiguous dispatch behavior;
- event replay/idempotency;
- inventory exact-Decimal and restart guarantees;
- API DTO isolation from secrets/vendor payloads;
- frontend capability/unsupported-state behavior;
- hardware validation separately from mocked/CI validation.

Architecture-significant changes must update the repository documentation or add/amend an ADR. Do not rely on chat memory to preserve a decision.
