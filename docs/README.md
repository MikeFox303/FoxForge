# FoxForge documentation

The Git repository is the canonical source for durable FoxForge architecture, contracts, project status and validation evidence.

## Read this first

- [Current project status](project-status.md) — current semantic release, validation candidate, implementation state and development order.
- [Pre-Alpha 5 Bambu physical validation](testing/pre-alpha-5-bambu-physical-validation.md) — exact installable candidate and X2D/AMS 2 Pro release gate.
- [Generic physical-validation runbook](testing/physical-validation-runbook.md) — version-independent evidence rules.
- [Physical evidence gate](testing/physical-evidence-gate.md) — verifier contract.
- [`CHANGELOG.md`](../CHANGELOG.md) — release and current-development summary.
- [`release/`](../release/) — immutable published release notes and release identity.

### Current identities

| Role | Identity |
| --- | --- |
| Latest semantic pre-release | `v0.1.0-alpha.4.3` |
| Target milestone | `v0.1.0-alpha.5` |
| Current Umbrel validation package | `0.1.0-alpha.4.3-umbrel.2` |
| Candidate source | `37b253f385c19451c7ea075a4a4d12378cf17cf2` |
| Candidate image | `ghcr.io/mikefox303/foxforge:sha-37b253f@sha256:e550c8026ed6ec80e973d91fe6d96cc1474d537ca87de7875ec54f4a03aaaa4f` |

The validation package is not a final Alpha 5 semantic release. Documentation-only commits may advance `main` without changing the immutable candidate under test.

## Architecture Decision Records

- [ADR 0001 — PrinterAdapter architecture](adr/0001-printer-adapter-architecture.md)
- [ADR 0002 — repository layout](adr/0002-repository-layout.md)
- [ADR 0003 — upstream architecture synthesis](adr/0003-upstream-architecture-synthesis.md)
- [ADR 0004 — command API security and idempotency](adr/0004-command-api-security.md)
- [ADR 0005 — browser command authentication and deployment trust](adr/0005-browser-command-authentication.md)

ADRs record durable decisions. Historical context inside an accepted ADR is not rewritten merely because implementation has advanced; implementation-status notes clarify current state.

## Printer and fleet design

- [Printer contracts v1](design/printer-contracts.md)
- [AdapterRegistry and FleetService](design/fleet-service.md)
- [Application-managed printer setup](design/app-managed-printer-setup.md)
- [Printer setup security](design/printer-setup-security.md)
- [Reconnect supervision and diagnostics](design/reconnect-supervision.md)
- [Common job control](design/job-control.md)
- [Realtime application events](design/realtime-events.md)
- [Upstream adoption map](design/upstream-adoption-map.md)

## Bambu Lab

- [Bambu adapter foundation](design/bambu-adapter-foundation.md)
- [Bambu LAN transport](design/bambu-lan-transport.md)
- [Bambu certificate trust](design/bambu-certificate-trust.md)
- [Bambu project storage](design/bambu-project-storage.md)
- [Pre-Alpha 5 physical validation](testing/pre-alpha-5-bambu-physical-validation.md)

Current source includes conservative LAN discovery, test-before-save setup, rollback-safe update, reconnect diagnostics, MQTT/TLS state, project-storage foundations and AMS/external material observation. Physical X2D/AMS 2 Pro acceptance remains the active release gate.

## Moonraker/Klipper

- [Moonraker adapter foundation](design/moonraker-adapter-foundation.md)
- [Moonraker HTTP/WebSocket transport](design/moonraker-http-transport.md)

The production transport foundation is implemented; representative physical OpenKE validation remains pending.

## Queue and inventory

Queue:

- [Queue dispatch](design/queue-dispatch.md)
- [Queue event lifecycle](design/queue-event-lifecycle.md)
- [Queue retry policy](design/queue-retry-policy.md)
- [Queue command API and artifact staging](design/queue-command-api.md)
- [Queue command UI](design/queue-command-ui.md)
- [Artifact lifecycle](design/artifact-lifecycle.md)

Inventory:

- [Inventory foundation](design/inventory-foundation.md)
- [SQLite inventory](design/inventory-sqlite.md)
- [Inventory atomicity](design/inventory-atomicity.md)

The normal spool operator workflow is implemented. Automatic queue-to-filament accounting remains a separate frozen P3 feature.

## API, web, security and persistence

- [Public API v1](design/public-api-v1.md)
- [Web UI foundation](design/web-ui-foundation.md)
- [Frontend parallel-development policy](design/frontend-parallel-development.md)
- [Command idempotency reservation](design/command-idempotency-reservation.md)
- [Secret storage](design/secret-storage.md)
- [Persistence migrations](design/persistence-migrations.md)
- [Printer setup UI acceptance](validation/printer-setup-ui-acceptance.md)

## Deployment and testing

- [Deployment overview](../deployment/README.md)
- [Docker deployment](../deployment/docker/README.md)
- [Umbrel deployment](../deployment/umbrel/README.md)
- [Deployment authentication contract](testing/deployment-auth-contract.md)
- [Coverage policy](testing/coverage-policy.md)

## Upstream/provenance records

- [`integrations/bambuddy/README.md`](../integrations/bambuddy/README.md) — retired fork/X2D experiment and upstream-contribution context.
- [`integrations/bambuddy/i18n_ru_uk.md`](../integrations/bambuddy/i18n_ru_uk.md) — localization contribution record.
- [`integrations/bambuddy/legacy_migration.md`](../integrations/bambuddy/legacy_migration.md) — historical migration/provenance notes.

These files are records, not a second FoxForge architecture.

## Historical evidence and dated records

- [Independent audit — 2026-09-04](audits/2026-09-04-independent-project-audit.md) — immutable historical finding snapshot.
- [Audit remediation tracker](audits/2026-09-04-remediation-tracker.md) — active status/evidence tracker.
- [`docs/status/`](status/) — dated release-readiness/evidence/handoff records. Alpha 4.x files here are historical and must not be used as the current validation target.
- [Umbrel mobile validation — 2026-09-04](validation/2026-09-04-umbrel-mobile.md) — historical Alpha 2 real-install/mobile evidence.
- [`testing/alpha4.2-validation-tooling-bootstrap.md`](testing/alpha4.2-validation-tooling-bootstrap.md) — historical Alpha 4.2 tooling handoff.
- [`testing/evidence/alpha4.2-manifest.template.json`](testing/evidence/alpha4.2-manifest.template.json) — historical Alpha 4.2 template.
- [P3 frozen state](status/p3-frozen-state-2026-09-04.md) — frozen implementation snapshot; current resume gate is defined by project-status/current physical-validation docs.

Do not rewrite immutable release notes, audit snapshots or dated evidence records to look current. Link to them with their historical role clearly labeled.

## Working rules

1. Important architecture/runtime decisions belong in the repository, not chat memory.
2. Common application code remains vendor-independent; deep Bambu behavior stays available through typed vendor capabilities.
3. Remote mutations remain authenticated, authorized, validated, idempotent, normalized and audited.
4. Physical/device/deployment claims require physical evidence; CI/QEMU/browser emulation are supporting evidence only.
5. Implementation work defines acceptance criteria and tests.
6. Copied/derived upstream material retains required copyright/license notices and provenance.
