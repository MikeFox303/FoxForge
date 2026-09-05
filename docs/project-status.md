# FoxForge project status

**Snapshot date:** 2026-09-05  
**Canonical branch:** `main`  
**Published pre-release:** `v0.1.0-alpha.4` (`0.1.0a4` backend package)  
**Frozen release commit:** `457f8f3f044147772b1ecf13df90b38a35268cda`  
**Published image:** `ghcr.io/mikefox303/foxforge:0.1.0-alpha.4`  
**Published multi-arch digest:** `sha256:0b0d96e5243db82ad3349bbc1c96243cbc6288c27eb716ff80512eb925b9fef4`  
**Umbrel Community App:** `my3d-foxforge` `0.1.0-alpha.4` merged to Store `main` via PR #26 as `de430fe63d79843b0a646851e8f03b05e37f624d`; representative physical Umbrel validation remains pending  
**Maturity:** runnable/installable alpha; not production-ready

This file is the concise current-state snapshot. ADRs/design documents remain normative for architecture, `CHANGELOG.md` remains implementation history, `release/` records immutable releases, and the independent audit/remediation tracker records stabilization evidence.

## Release/source boundary

`v0.1.0-alpha.4` is the current published FoxForge pre-release. Its guarded release workflow froze release identity, ran backend/frontend validation, built and smoke-tested the unified image, published Linux `amd64` + `arm64` with SBOM/provenance and only then created the Git tag and GitHub pre-release.

The release includes P1 common job control, P2 realtime application events, the complete normal inventory operator workflow and the independent-audit software stabilization foundation. These are no longer “post-alpha.3 current-source only” features.

The companion Umbrel package now matches that release: Store PR #26 pins the exact immutable digest and maps Umbrel `APP_PASSWORD` to `FOXFORGE_COMMAND_TOKEN` while keeping App Proxy as a separate defense-in-depth boundary. Its final package/Compose and anonymous `amd64`/`arm64` runtime gates were green before merge.

Documentation-only synchronization after the release does not change the immutable `alpha.4` image. Any future code change requires another guarded release before versioned deployments receive it.

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, snapshots/events/errors and typed capabilities. |
| Bambu adapter | Implemented foundation | MQTT/TLS, project storage and common job controls; optional independent MQTT/FTPS SHA-256 certificate pins; physical X2D validation pending. |
| Moonraker adapter | Implemented foundation | HTTP/WebSocket, upload/start and common job controls; explicit endpoint/redirect/address-resolution security policy; physical OpenKE validation pending. |
| Fleet management | Implemented | Dynamic composition, normalized lifecycle/events and per-printer reconnect supervision. |
| Durable print queue | Implemented foundation | SQLite-backed dispatch, retry boundaries, terminal persistence and explicit `INDETERMINATE`. |
| Artifact staging | Implemented | Content-addressed storage, quota/min-free reserve, retention and safe orphan cleanup. |
| Filament/spool inventory | Operator workflow implemented | Exact `Decimal` ledger, idempotent/atomic adjustments, opaque physical assignments, create/correct/empty-mass/move/unassign/archive/history UI and production-browser acceptance. |
| Public API/read models | Implemented | FoxForge DTOs only; no raw vendor payloads, secrets or local paths. |
| Command security | Implemented foundation | Auth, permission checks, request IDs, durable idempotency, normalized errors and append-only audit. |
| Printer credentials | SecretStore boundary implemented | Bambu access code and Moonraker API key are separated from normal runtime config; legacy inline credentials migrate. |
| Common Pause/Resume/Cancel | Implemented and released in `alpha.4` | Exact vendor-job identity guards and non-retryable ambiguous outcomes; physical validation pending. |
| Realtime application events | Implemented and released in `alpha.4` | SSE replay/resync invalidation layer; canonical HTTP snapshots and polling fallback remain. |
| Web UI | Functional alpha | Printer setup, queue command flow, common controls, realtime invalidation and the normal inventory operator workflow are implemented. |
| Browser acceptance | Implemented | Production-container Playwright desktop/tablet/phone matrix covers routing, Add Printer, write bootstrap, file staging/enqueue, realtime resync and representative inventory operations. |
| Dependency/security governance | Implemented | Frozen dependency graphs, Dependabot, npm/pip audits and final-image HIGH/CRITICAL scanning. |
| Backend coverage governance | Implemented | Approximately 76% measured branch-aware baseline; CI enforces a 75% floor on Python 3.12 while Python 3.13 runs the suite independently. |
| Docker/ARM64 | Published alpha foundation | `alpha.4` is published for Linux `amd64` + `arm64`; representative Raspberry Pi 5 validation pending. |
| Umbrel | `alpha.4` package merged and CI-validated | Store `main` pins the exact release digest and supplies `APP_PASSWORD` → `FOXFORGE_COMMAND_TOKEN`; real Raspberry Pi/Umbrel/proxy/printer-network evidence remains required. |
| Automatic filament accounting | **Frozen draft** | Preserved in PR #58 and explicitly not merged into `main`; see the P3 freeze/resume gate. |
| Farm scheduler | Not implemented | Deferred until queue/control/inventory/deployment foundations and P3 are stable. |

## Persistence state

Current owned persistent versions are:

- `config.json`: `schemaVersion` **2**;
- `foxforge.sqlite3`: SQLite `PRAGMA user_version` **1**;
- `secrets.json`: SecretStore format version **1**.

Migrations, backups and schema validation are part of `alpha.4`. Complete `/data` backups must be treated as sensitive because printer credentials and recovery material may be present.

## Stabilization/audit state

The immutable finding snapshot is [the 2026-09-04 independent audit](audits/2026-09-04-independent-project-audit.md). Active evidence/status is maintained in the [remediation tracker](audits/2026-09-04-remediation-tracker.md).

All software-only audit findings have repository remediation evidence. The findings still not `RESOLVED` are validation-bound:

- **AUD-003 — VALIDATION REQUIRED:** the `alpha.4` package now has the required application credential/bootstrap software contract, but representative Raspberry Pi/Umbrel package installation, restart/persistence, actual proxy write path, direct-backend fail-closed behavior, deployment-network printer reachability, upgrade and SSE reconnect/resync evidence are still required;
- **AUD-013 — VALIDATION REQUIRED:** Bambu certificate-pinning software foundation exists, but real X2D MQTT/FTPS certificate observations are required before changing trust defaults.

**AUD-004 remains resolved**: the explicit-token ADR 0005 trust model is backed by production fail-closed and representative reverse-proxy tests. App Proxy/forwarded identity metadata is defense in depth and does not become a FoxForge principal.

The normal inventory operator workflow required by the P3 resume gate is implemented and released in `alpha.4`. That does not by itself authorize P3 to resume: the physical/deployment validation gate remains binding.

## Safety invariants that remain binding

1. Common application/domain code must not import Bambu or Moonraker transport/protocol types.
2. Deep Bambu behavior remains behind typed capabilities rather than being flattened into common lowest-common-denominator fields.
3. Common job controls target an exact observed vendor job identity and fail closed on stale/mismatched state.
4. Ambiguous pause/resume/cancel side effects are non-retryable; unresolved same-key HTTP replay never repeats the device command.
5. Queue code never guesses whether an ambiguous print started; `INDETERMINATE` requires reconciliation and is never automatically retried.
6. Receipt-bearing jobs are never redispatched.
7. Realtime events are invalidations, not a second source of truth; continuity uncertainty forces canonical HTTP resync.
8. Queue/inventory realtime events are emitted only after successful persistence.
9. Inventory owns FoxForge spool identity; printer slots remain opaque physical identifiers.
10. Public API DTOs expose FoxForge contracts, not raw vendor payloads, secrets or arbitrary local paths.
11. Browser code cannot weaken backend retry/idempotency/reconciliation semantics.
12. Docker and Umbrel package the same application behavior; deployment proxy authentication is defense in depth, not a replacement for FoxForge authorization.
13. Scheduler/farm logic must depend on FoxForge capabilities and durable application state, never directly on vendor transports.

## Hardware/deployment validation boundary

Automated gates validate code, packaging and browser behavior but do not replace physical testing.

### Bambu X2D

Record real-device evidence for connection/reconnect, state synchronization, MQTT and FTPS certificate behavior, project delivery, print-start acknowledgement, pause/resume/cancel, lifecycle completion and ambiguous-outcome reconciliation.

### Moonraker/OpenKE

Record real-device evidence for HTTP/WebSocket connectivity, actual endpoint-policy compatibility, upload/checksum/start, pause/resume/cancel and lifecycle completion/failure handling.

### Raspberry Pi 5 / Umbrel

Record installation/restart/persistence of the published `alpha.4` package, X2D/OpenKE reachability from the actual Umbrel network, authenticated write behavior through the real proxy path, direct-backend fail-closed behavior, upgrades and representative SSE reconnect/resync behavior.

Until these matrices are recorded, documentation must not describe the transports or full deployment as production-validated.

## Automatic filament accounting freeze

P3 is **not the current active implementation priority**. Its partially implemented work is intentionally preserved in draft PR #58 so it can be resumed without losing design effort.

The canonical frozen-state record is [P3 automatic filament accounting — frozen implementation state](status/p3-frozen-state-2026-09-04.md).

The software prerequisites now satisfied by `alpha.4` include:

- release/dependency/security/migration/atomic-inventory stabilization required by the audit;
- browser/deployment trust contract and representative proxy acceptance;
- normal inventory create/correct/empty-mass/move/assign/unassign/archive/history workflow;
- production-container browser acceptance for representative inventory operations;
- common job control and realtime application-event foundations;
- an exact immutable `alpha.4` Umbrel package with an ADR-0005-compatible application credential path.

P3 still may not resume until the remaining physical/deployment gate is satisfied. At minimum:

- representative X2D, Moonraker/OpenKE and Raspberry Pi/Umbrel validation is recorded where required;
- PR #58 is synchronized with the then-current `main` without discarding remediation work;
- backend Python 3.12/3.13, coverage floor, frontend TypeScript/Vitest/build, production-container browser acceptance, unified-container smoke and security gates are green on the exact final P3 head;
- P3 design/status/changelog documentation is synchronized before merge.

## Current development order

1. **Physical/deployment validation:** X2D, Moonraker/OpenKE and the published `alpha.4` package on representative Raspberry Pi/Umbrel, including remaining AUD-003/AUD-013 evidence.
2. **Audit closure/documentation:** record real-device/package evidence and keep README/status/deployment claims aligned with what was actually tested.
3. **Resume P3 only after the gate:** synchronize draft PR #58 with current `main`, finish tests/docs and merge only on exact-head green evidence.
4. **Farm/deep-vendor expansion:** persistent scheduler/farm semantics and deeper Bambu features follow after the preceding foundations are stable.

The inventory operator workflow is no longer an outstanding development-order item. Historical alpha release notes and the original audit snapshot are not rewritten.

## Current validation gates

Repository changes are protected by the applicable combination of:

- Ruff lint/format;
- full Python tests on 3.12 and 3.13;
- measured backend branch coverage with a 75% floor on Python 3.12;
- frozen dependency verification;
- frontend TypeScript checks, Vitest and production build;
- production-container Playwright acceptance on desktop/tablet/phone;
- unified Docker image build/start/health/runtime smoke;
- npm/pip dependency audits;
- final-image HIGH/CRITICAL vulnerability scanning;
- guarded release identity checks and immutable multi-arch release publication.

The companion Store separately validates the exact Umbrel package definition, Compose rendering, application-token bootstrap and anonymous multi-architecture runtime pull/start. Physical validation remains a separate requirement wherever a finding or production claim depends on real printer/proxy behavior.

## Key documents

- [Release notes — v0.1.0-alpha.4](../release/v0.1.0-alpha.4.md)
- [Independent audit](audits/2026-09-04-independent-project-audit.md)
- [Audit remediation tracker](audits/2026-09-04-remediation-tracker.md)
- [P3 frozen state / resume gate](status/p3-frozen-state-2026-09-04.md)
- [ADR 0001 — PrinterAdapter architecture](adr/0001-printer-adapter-architecture.md)
- [ADR 0005 — browser command authentication/deployment trust](adr/0005-browser-command-authentication.md)
- [Bambu LAN transport](design/bambu-lan-transport.md)
- [Bambu certificate trust](design/bambu-certificate-trust.md)
- [Moonraker transport](design/moonraker-http-transport.md)
- [Secret storage](design/secret-storage.md)
- [Persistence migrations](design/persistence-migrations.md)
- [Inventory atomicity](design/inventory-atomicity.md)
- [Realtime application events](design/realtime-events.md)
- [Coverage policy](testing/coverage-policy.md)

## Release readiness

FoxForge is suitable for continued alpha development and controlled self-hosted testing. `v0.1.0-alpha.4` is a real published guarded pre-release and the matching Umbrel package is now merged in Store `main`, but FoxForge is **not production-ready** and must not be represented as physically validated until the remaining printer/deployment matrices are complete.
