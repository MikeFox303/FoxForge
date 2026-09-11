# FoxForge documentation

The Git repository is the canonical source for durable FoxForge architecture, contracts, validation evidence and release state. Chat discussion is not a substitute for the documents below.

## Read this first

- [Current project status](project-status.md) — current semantic release, validation candidate, implementation state and development order.
- [Pre-Alpha 5 Bambu physical validation](testing/pre-alpha-5-bambu-physical-validation.md) — exact Candidate 7 identity and X2D/AMS 2 Pro release gate.
- [Generic physical-validation runbook](testing/physical-validation-runbook.md) — version-independent evidence rules.
- [Physical evidence gate](testing/physical-evidence-gate.md) — verifier contract.

## Current validation target

| Item | Current value |
| --- | --- |
| Semantic release | `v0.1.0-alpha.4.3` |
| Target semantic release | `v0.1.0-alpha.5` — unpublished |
| Active milestone | Pre-Alpha 5 / Bambu Lab connection and control |
| Candidate 7 application source | `4f769ca89d466d2cbe41360848b6343ec5a8eb36` |
| Candidate 7 exact image | `ghcr.io/mikefox303/foxforge:sha-4f769ca@sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7` |
| Candidate 7 Umbrel package | `0.1.0-alpha.4.3-umbrel.7` |
| Candidate 7 Store commit | `6e69e4005ae9529eeee5c376c8769393b056ee0d` |
| Physical validation | **Authorized; no-print gate not yet accepted** |

Candidate 5 is historical after real X2D partial-status/dual-external findings. Candidate 6 is historical/failed after real X2D UI Verify could succeed and Add Printer could then fail with `internal_adapter_error`. PR #184 fixed the Add/MQTT lifecycle, so Candidate 7 is the required replacement identity. Candidate 5/6 evidence must not be relabeled as Candidate 7 evidence.

The frozen Candidate 7 application source passed the full exact-source software gate. Its immutable multi-architecture image was verified with independent anonymous pulls, and the companion Store package passed package/runtime gates on both `amd64` and `arm64` before merge. Documentation-only commits may advance `main` after this freeze, but physical evidence must always name the frozen source/image/package/Store identity it actually validates.

## Architecture Decision Records

- [ADR 0001 — PrinterAdapter architecture](adr/0001-printer-adapter-architecture.md)
- [ADR 0002 — repository layout](adr/0002-repository-layout.md)
- [ADR 0003 — upstream architecture synthesis](adr/0003-upstream-architecture-synthesis.md)
- [ADR 0004 — command API security and idempotency](adr/0004-command-api-security.md)
- [ADR 0005 — browser command authentication and deployment trust](adr/0005-browser-command-authentication.md)

ADRs record durable decisions. Historical context inside an accepted ADR is not rewritten merely because implementation has advanced; implementation-status notes clarify current state.

## Printer and fleet design

- [Printer contracts v1](design/printer-contracts.md)
- [Material topology capability](design/material-topology.md)
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
- [Private discovery subnet suggestions](design/private-discovery-subnet-suggestions.md)
- [Bambu certificate trust](design/bambu-certificate-trust.md)
- [Bambu project storage](design/bambu-project-storage.md)
- [Pre-Alpha 5 Candidate 7 physical validation](testing/pre-alpha-5-bambu-physical-validation.md)

Current application source includes bounded LAN discovery with private-subnet suggestions, staged exact-payload setup, a single backend-authoritative live Add connection, rollback-safe Update, reconnect diagnostics, MQTT/TLS state, per-session Bambu MQTT client IDs, project storage, AMS/external observation, typed material topology, common thermal telemetry and fail-closed 3MF material routing. Candidate 7 is published; physical X2D/AMS 2 Pro acceptance is now the active gate.

## Moonraker/Klipper

- [Moonraker adapter foundation](design/moonraker-adapter-foundation.md)
- [Moonraker HTTP/WebSocket transport](design/moonraker-http-transport.md)

The production transport foundation is implemented; representative physical OpenKE validation remains pending and does not inherit Bambu evidence.

## Queue and inventory

Queue:

- [Queue dispatch](design/queue-dispatch.md)
- [Queue event lifecycle](design/queue-event-lifecycle.md)
- [Queue retry policy](design/queue-retry-policy.md)
- [Queue command API and artifact staging](design/queue-command-api.md)
- [Queue command UI](design/queue-command-ui.md)
- [Artifact lifecycle](design/artifact-lifecycle.md)
- [Immutable 3MF print-plan inspection](design/immutable-3mf-print-plan.md)

Inventory:

- [Inventory domain](design/inventory-domain.md)
- [Inventory operator API](design/inventory-command-api.md)
- [Inventory command UI](design/inventory-command-ui.md)

The normal spool operator workflow is implemented. Automatic queue-to-filament accounting P3 R1–R5 is software-integrated. Candidate 7's Umbrel package enables the provider-scoped `bambu-validation` mode; physical Bambu accounting acceptance remains pending. Moonraker/Klipper automatic accounting is not enabled by this mode.

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
- [Deployment authentication](../deployment/README.md#write-authentication)
- [Semantic release workflow](../.github/workflows/release.yml)
- [Legacy Candidate 6 software gate / Candidate 7 exact-source gate](testing/pre-alpha-5-candidate6-software-gate.md)
- [Candidate 7 physical-validation runbook](testing/pre-alpha-5-bambu-physical-validation.md)
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
- [`docs/status/`](status/) — dated release-readiness/evidence/handoff records. Older candidate records are historical and must not be used as the current validation target.
- [Umbrel mobile validation — 2026-09-04](validation/2026-09-04-umbrel-mobile.md) — historical Alpha 2 real-install/mobile evidence.
- [`testing/alpha4.2-validation-tooling-bootstrap.md`](testing/alpha4.2-validation-tooling-bootstrap.md) — historical Alpha 4.2 tooling handoff.
- [`testing/evidence/alpha4.2-manifest.template.json`](testing/evidence/alpha4.2-manifest.template.json) — historical Alpha 4.2 template.
- [P3 frozen-state history](status/p3-frozen-state-2026-09-04.md) — historical implementation snapshot; current integrated state is recorded in `project-status.md`.
