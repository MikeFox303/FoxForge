# FoxForge project status

**Snapshot date:** 2026-09-05  
**Canonical branch:** `main`  
**Published pre-release:** `v0.1.0-alpha.4.2` (`0.1.0a4.post2` backend package)  
**Frozen release commit:** `fe5b3437f1e342548df74ded78557c771ef40710`  
**Published image:** `ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2`  
**Published multi-arch digest:** `sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6`  
**Umbrel Community App:** `my3d-foxforge` `0.1.0-alpha.4.2`, merged to Store `main` via PR #28 as `e842c411e26689609e9bbba4681df903f3624bbd`  
**Maturity:** runnable/installable alpha; not production-ready

This file is the concise current-state snapshot. ADRs/design documents remain normative for architecture, `CHANGELOG.md` remains implementation history, `release/` records immutable release metadata/notes, and the independent audit/remediation tracker records stabilization evidence.

## Release and deployment state

`v0.1.0-alpha.4.2` is the current published FoxForge pre-release. Release workflow `33973431720` ran on exact commit `fe5b3437f1e342548df74ded78557c771ef40710` and completed successfully. The annotated tag resolves to that exact commit.

The guarded release sequence performs backend/frontend checks, builds and smoke-tests the production image, runs exact-commit Browser Acceptance, verifies source-map absence and revalidates immutable release identity before the Git tag is created. The release then publishes the versioned Linux `amd64` + `arm64` image and creates the GitHub pre-release.

The published OCI index is:

```text
ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6
```

The matching Umbrel package is already merged in `MikeFox303/umbrel-3d-printing-store` at commit `e842c411e26689609e9bbba4681df903f3624bbd`. It preserves `${APP_DATA_DIR}/data:/data` and maps Umbrel `APP_PASSWORD` to `FOXFORGE_COMMAND_TOKEN`. PR-head and post-merge Store gates passed.

Durable release/publication evidence is recorded in [`status/alpha4-fix2-release-evidence-2026-09-05.md`](status/alpha4-fix2-release-evidence-2026-09-05.md).

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, snapshots/events/errors and typed capabilities. |
| Bambu adapter | Implemented foundation | MQTT/TLS, project storage and common job controls; optional independent MQTT/FTPS SHA-256 certificate pins; physical X2D validation pending. |
| Moonraker adapter | Implemented foundation | HTTP/WebSocket, upload/start and common job controls; explicit endpoint/redirect/address-resolution security policy; physical OpenKE validation pending. |
| Fleet management | Implemented | Dynamic composition, normalized lifecycle/events and per-printer reconnect supervision. |
| Durable print queue | Implemented foundation | SQLite-backed dispatch, retry boundaries, terminal persistence and explicit `INDETERMINATE`. |
| Artifact staging | Implemented | Content-addressed storage, quota/min-free reserve, retention and safe orphan cleanup. |
| Filament/spool inventory | Operator workflow implemented | Exact `Decimal` ledger, idempotent/atomic adjustments, opaque physical assignments and create/correct/empty-mass/move/unassign/archive/history UI. |
| Public API/read models | Implemented | FoxForge DTOs only; no raw vendor payloads, secrets or local paths. |
| Command security | Implemented foundation | Auth, permission checks, request IDs, durable idempotency, normalized errors and append-only audit. |
| Printer credentials | SecretStore boundary implemented | Bambu access code and Moonraker API key are separated from normal runtime config; legacy inline credentials migrate. |
| Pause/Resume/Cancel | Implemented/released | Exact vendor-job identity guards and non-retryable ambiguous outcomes; physical validation pending. |
| Realtime application events | Implemented/released | SSE replay/resync invalidation layer; canonical HTTP snapshots and polling fallback remain. |
| Web UI | Functional alpha | Printer setup, queue command flow, common controls, realtime invalidation and normal inventory workflow. |
| Responsive/browser acceptance | Implemented | Exact release Browser Acceptance covers phone 390×844, tablet 900×1024, desktop 1920×1080 and ultra-wide 5120×1440 plus RU/UK, Add Printer, Operator Access and browser-runtime errors. |
| Dependency/security governance | Implemented | Frozen dependency graphs, Dependabot, npm/pip audits and final-image HIGH/CRITICAL scanning. |
| Backend coverage governance | Implemented | Approximately 76% measured branch-aware baseline; CI enforces a 75% floor on Python 3.12 while Python 3.13 runs independently. |
| Docker/ARM64 | Published alpha foundation | Alpha 4.2 published for Linux `amd64` + `arm64`; representative Raspberry Pi 5 validation pending. |
| Umbrel | Alpha 4.2 package merged and CI-validated | Exact digest pin plus `APP_PASSWORD` → `FOXFORGE_COMMAND_TOKEN`; real Raspberry Pi/Umbrel/proxy/printer-network evidence still required. |
| Automatic filament accounting | **Frozen draft** | Preserved in draft PR #58 and not merged into `main`; see P3 freeze/resume gate. |
| Farm scheduler | Not implemented | Deferred until queue/control/inventory/deployment foundations and P3 are stable. |

## Persistence state

Current owned persistent versions are:

- `config.json`: `schemaVersion` **2**;
- `foxforge.sqlite3`: SQLite `PRAGMA user_version` **1**;
- `secrets.json`: SecretStore format version **1**.

Migrations, backups and schema validation are implemented. Complete `/data` backups must be treated as sensitive because printer credentials and recovery material may be present.

## Audit and physical-validation state

The immutable finding snapshot is [the 2026-09-04 independent audit](audits/2026-09-04-independent-project-audit.md). Active evidence/status is maintained in the [remediation tracker](audits/2026-09-04-remediation-tracker.md).

All software-only audit findings have repository remediation evidence. The remaining findings are validation-bound:

- **AUD-003 — `VALIDATION REQUIRED`:** representative Raspberry Pi 5/Umbrel package installation, restart/persistence, real proxy write path, direct-backend fail-closed behavior, deployment-network printer reachability, upgrade and SSE reconnect/resync evidence is still required.
- **AUD-013 — `VALIDATION REQUIRED`:** real X2D MQTT/FTPS certificate stability, correct-pin behavior, wrong-pin fail-closed behavior and recovery evidence is still required.

The current canonical physical-test target is the exact Alpha 4.2 package/image/Store commit listed above. [`testing/physical-validation-runbook.md`](testing/physical-validation-runbook.md) now contains those identities and the secret-safe evidence workflow.

Automated CI, QEMU, mocks, browser emulation and Store package smoke tests do **not** count as real-device validation.

## Safety invariants that remain binding

1. Common application/domain code must not import Bambu or Moonraker transport/protocol types.
2. Deep Bambu behavior remains behind typed capabilities instead of being flattened into common lowest-common-denominator fields.
3. Common job controls target an exact observed vendor job identity and fail closed on stale/mismatched state.
4. Ambiguous pause/resume/cancel or print-start side effects are never blindly retried.
5. Receipt-bearing jobs are never redispatched.
6. Realtime events are invalidations, not a second source of truth; continuity uncertainty forces canonical HTTP resync.
7. Queue/inventory realtime events publish only after successful persistence.
8. Inventory owns FoxForge spool identity; printer slots remain opaque physical identifiers.
9. Public API DTOs expose FoxForge contracts, not raw vendor payloads, secrets or arbitrary local paths.
10. Browser code cannot weaken backend retry/idempotency/reconciliation semantics.
11. Docker and Umbrel package the same application behavior; deployment proxy authentication is defense in depth, not a replacement for FoxForge authorization.
12. Scheduler/farm logic must depend on FoxForge capabilities and durable application state, never directly on vendor transports.

## Automatic filament accounting freeze

P3 automatic filament accounting remains preserved in draft PR #58 and is **not** the active implementation priority until the real-device/deployment gate passes.

The canonical frozen-state record is [P3 automatic filament accounting — frozen implementation state](status/p3-frozen-state-2026-09-04.md).

Software prerequisites already satisfied include the release/dependency/security/migration/atomic-inventory stabilization, browser/deployment trust contract, normal inventory workflow, production-container browser acceptance, common job control/realtime foundations and an exact immutable Umbrel package with an ADR-0005-compatible application credential path.

P3 may resume only after representative Alpha 4.2 physical/deployment evidence is recorded, `AUD-003`/`AUD-013` evidence requirements are met, PR #58 is synchronized with then-current `main`, and all exact-head backend/frontend/container/security/browser gates pass again.

## Current development order

1. **Physical/deployment validation:** Raspberry Pi 5/Umbrel + Bambu X2D/AMS 2 Pro + Ender 3 V3 KE/OpenKE using the exact Alpha 4.2 package.
2. **Audit closure:** review secret-safe evidence and update AUD-003/AUD-013 only when their verifier/observation requirements actually pass.
3. **Resume P3:** synchronize draft PR #58 with current `main`, preserve all stabilization work, finish tests/docs and merge only on exact-head green evidence.
4. **Farm/deep-vendor expansion:** persistent scheduler/farm semantics, AMS/CFS depth and other Bambu-specific capabilities follow after the preceding foundations are stable.

Historical release notes and the original audit snapshot are not rewritten.

## Current validation gates

Repository changes are protected by the applicable combination of:

- Ruff lint/format;
- full Python tests on 3.12 and 3.13;
- measured backend branch coverage with a 75% floor on Python 3.12;
- frozen dependency verification;
- frontend TypeScript checks, Vitest and production build;
- production-container Playwright acceptance on the supported viewport matrix;
- unified Docker image build/start/health/runtime smoke;
- deployment-authentication acceptance;
- npm/pip dependency audits;
- final-image HIGH/CRITICAL vulnerability scanning;
- guarded release identity checks and immutable multi-arch release publication.

The companion Store separately validates the exact Umbrel package definition, Compose rendering, application-token bootstrap and anonymous architecture runtime pull/start. Physical validation remains separate.

## Key documents

- [Release notes — v0.1.0-alpha.4.2](../release/v0.1.0-alpha.4.2.md)
- [Alpha 4.2 release evidence](status/alpha4-fix2-release-evidence-2026-09-05.md)
- [Physical validation runbook](testing/physical-validation-runbook.md)
- [Physical evidence gate](testing/physical-evidence-gate.md)
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

FoxForge is suitable for continued alpha development and controlled self-hosted testing. `v0.1.0-alpha.4.2` is a real guarded pre-release and the matching Umbrel package is merged in Store `main`, but FoxForge is **not production-ready** and must not be represented as physically validated until the remaining printer/deployment matrices are complete.
