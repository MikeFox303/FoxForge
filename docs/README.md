# FoxForge documentation

The Git repository is the canonical source for durable FoxForge architecture, contracts, validation evidence and release state. Chat discussion is not a substitute for the documents below.

## Read this first

- [Current project status](project-status.md) — current semantic release, immutable validation candidate, implementation state and next gate.
- [Pre-Alpha 5 Bambu physical validation](testing/pre-alpha-5-bambu-physical-validation.md) — exact Candidate 6 identity and X2D/AMS 2 Pro physical acceptance procedure.
- [Candidate 6 software gate](testing/pre-alpha-5-candidate6-software-gate.md) — exact-source pre-publication software gate and C6-11 handoff.
- [Generic physical-validation runbook](testing/physical-validation-runbook.md) — version-independent evidence rules.
- [Physical evidence gate](testing/physical-evidence-gate.md) — verifier contract.

## Current validation target

| Item | Current value |
| --- | --- |
| Semantic release | `v0.1.0-alpha.4.3` |
| Target semantic release | `v0.1.0-alpha.5` — **not published** |
| Active milestone | Pre-Alpha 5 / Bambu Lab connection and control |
| Candidate 6 application source | `78ace6f7b7412aa0d3fc58bed095aecdf9920f94` |
| Candidate 6 image | `ghcr.io/mikefox303/foxforge:sha-78ace6f` |
| Candidate 6 OCI digest | `sha256:b01f1d44199a4413167ee2369c0dfbcafa602312442772d27de18e04c24ed0eb` |
| Candidate 6 Umbrel package | `0.1.0-alpha.4.3-umbrel.6` |
| Candidate 6 Store commit | `018d29a8668e923c7f1a3447fc12273939aefbb8` |
| C6-10 exact-main gate | **PASS** on frozen source in run `34439269464` |
| C6-11 publication | **PASS** — OCI + Store package published and post-merge runtime verified |
| Physical Candidate 6 validation | **Authorized, not yet completed** |

Publication verification is recorded by FoxForge workflow run `34440021792`; the merged Umbrel package passed post-merge package/runtime run `34509996521` and Store release gate `34509996582`.

Candidate 5 is historical/failed for Alpha 5 acceptance and remains relevant only as prior diagnostic evidence. Candidate 1–5 evidence must not be relabeled as Candidate 6 evidence. Documentation-only commits may advance repository `main` after the runtime candidate was frozen; all physical evidence must continue naming the frozen source/image/package/Store identity above.

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
- [Pre-Alpha 5 physical validation](testing/pre-alpha-5-bambu-physical-validation.md)

Current Candidate 6 includes bounded LAN discovery, test-before-save setup, rollback-safe update, reconnect diagnostics, MQTT/TLS state, project storage, AMS/external observation, typed material topology, common thermal telemetry and fail-closed 3MF material routing. The software/publication gates are complete; the real Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro physical gate is next.

## Moonraker/Klipper

- [Moonraker adapter foundation](design/moonraker-adapter-foundation.md)
- [Moonraker HTTP/WebSocket transport](design/moonraker-http-transport.md)

The production transport foundation is implemented; representative physical OpenKE validation remains pending. Candidate 6 `bambu-validation` accounting mode does not enable automatic Moonraker accounting enforcement.

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

Automatic queue-to-filament accounting P3 R1–R5 is software-integrated. The published Candidate 6 Umbrel package intentionally enables the provider-scoped `bambu-validation` gate so Bambu accounting can now be validated physically with explicit reservations and weighed-spool evidence. Moonraker/Klipper enforcement remains disabled.

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
- [Candidate 6 software gate](testing/pre-alpha-5-candidate6-software-gate.md)
- [Deployment authentication contract](testing/deployment-auth-contract.md)
- [Coverage policy](testing/coverage-policy.md)

## Upstream/provenance records

- [`integrations/bambuddy/README.md`](../integrations/bambuddy/README.md) — retired fork/X2D experiment and upstream-contribution context.
- [`integrations/bambuddy/i18n_ru_uk.md`](../integrations/bambuddy/i18n_ru_uk.md) — localization contribution record.
- [`integrations/bambuddy/legacy_migration.md`](../integrations/bambuddy/legacy_migration.md) — historical migration/provenance notes.

These files are records, not a second FoxForge architecture. Any copied or derived upstream code must retain required copyright/license/provenance notices.

## Historical evidence and dated records

- [Independent audit — 2026-09-04](audits/2026-09-04-independent-project-audit.md) — immutable historical finding snapshot.
- [Audit remediation tracker](audits/2026-09-04-remediation-tracker.md) — active status/evidence tracker.
- [`docs/status/`](status/) — dated release-readiness/evidence/handoff records; older Alpha 4.x candidate files remain historical.
- [Umbrel mobile validation — 2026-09-04](validation/2026-09-04-umbrel-mobile.md) — historical Alpha 2 real-install/mobile evidence.
- [P3 frozen-state history](status/p3-frozen-state-2026-09-04.md) — historical implementation snapshot; current integrated state is recorded in `project-status.md`.
