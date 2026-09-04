# FoxForge project status

**Snapshot date:** 2026-09-05  
**Canonical branch:** `main`  
**Published pre-release:** `v0.1.0-alpha.3` (`0.1.0a3` backend package)  
**Current source:** `alpha.3` foundation + P1 common job control + P2 realtime events + independent-audit stabilization  
**Umbrel Community App:** `my3d-foxforge`, still pinned to immutable `alpha.3`  
**Maturity:** runnable/installable alpha; not production-ready

This file is the concise current-source snapshot. ADRs/design documents remain normative for architecture, `CHANGELOG.md` remains implementation history, `release/` records immutable releases, and the independent audit/remediation tracker records stabilization evidence.

## Release/source boundary

The published `v0.1.0-alpha.3` image is immutable. Current `main` has moved substantially beyond that release. P1, P2 and the later stabilization work require a new guarded release before versioned Docker/Umbrel users receive them.

Do not infer current-source behavior from the shipped alpha.3 image, and do not rewrite historical release notes to describe later work.

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, snapshots/events/errors and typed capabilities. |
| Bambu adapter | Implemented foundation | MQTT/TLS, project storage and P1 controls; optional independent MQTT/FTPS SHA-256 certificate pins; physical X2D validation pending. |
| Moonraker adapter | Implemented foundation | HTTP/WebSocket, upload/start and P1 controls; explicit endpoint/redirect/address-resolution security policy; physical OpenKE validation pending. |
| Fleet management | Implemented | Dynamic composition, normalized lifecycle/events and reconnect supervision. |
| Durable print queue | Implemented foundation | SQLite-backed dispatch, retry boundaries, terminal persistence and explicit `INDETERMINATE`. |
| Artifact staging | Implemented | Content-addressed storage, quota/min-free reserve, retention and safe orphan cleanup. |
| Filament/spool inventory | Durable foundation implemented | Exact `Decimal` ledger, idempotent adjustments, atomic balance mutation and physical assignments. |
| Public API/read models | Implemented | FoxForge DTOs only; no raw vendor payloads, secrets or local paths. |
| Command security | Implemented foundation | Auth, permission checks, request IDs, durable idempotency, normalized errors and append-only audit. |
| Printer credentials | SecretStore boundary implemented | Bambu access code and Moonraker API key are separated from normal runtime config; legacy inline credentials migrate. |
| Common Pause/Resume/Cancel | Implemented post-alpha.3 (P1) | Exact vendor-job identity guards and non-retryable ambiguous outcomes; physical validation pending. |
| Realtime application events | Implemented post-alpha.3 (P2) | SSE replay/resync invalidation layer; canonical HTTP snapshots and polling fallback remain. |
| Web UI | Functional alpha | Printer setup, queue command flow, P1 controls and P2 invalidation implemented; normal inventory operator workflow remains incomplete. |
| Browser acceptance | Implemented | Production-container Playwright desktop/tablet/phone matrix includes routing, Add Printer keyboard behavior, write bootstrap, file staging/enqueue, truthful disabled states and realtime resync. |
| Dependency/security governance | Implemented | Frozen dependency graphs, Dependabot, npm/pip audits and final-image HIGH/CRITICAL scan. |
| Backend coverage governance | Implemented | 76% measured branch-aware baseline; CI enforces a 75% floor on Python 3.12 while Python 3.13 runs the full suite independently. |
| Docker/ARM64 | Implemented foundation | Unified image and multi-arch release foundation exist; representative Raspberry Pi validation pending. |
| Umbrel | Released alpha.3 package only | Current post-alpha.3 source is not yet shipped; representative authenticated proxy/write validation pending. |
| Automatic filament accounting | **Frozen draft** | Preserved in PR #58 and explicitly not merged into `main`; see the P3 freeze/resume gate. |
| Farm scheduler | Not implemented | Deferred until queue/control/inventory/deployment foundations and P3 are stable. |

## Stabilization/audit state

The immutable finding snapshot is [the 2026-09-04 independent audit](audits/2026-09-04-independent-project-audit.md). Active evidence/status is maintained in the [remediation tracker](audits/2026-09-04-remediation-tracker.md).

The stabilization sequence has already resolved the release-integrity, duplicate-launcher, reproducible dependency, persistence migration, atomic inventory, artifact lifecycle, reconnect scalability, Moonraker endpoint security, SecretStore, browser acceptance and coverage-governance findings.

The remaining blockers are principally **physical/deployment validation**, not permission to resume feature work automatically:

- **AUD-003:** representative write-capable deployment/Umbrel package validation still required;
- **AUD-004:** representative authenticated reverse-proxy/Umbrel trust-boundary validation still required;
- **AUD-013:** Bambu certificate-pinning software foundation exists, but real X2D certificate observations are required before changing trust defaults.

## P1/P2 safety invariants that remain binding

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
12. Docker and Umbrel package the same application behavior; the deployment proxy is defense in depth, not a replacement for FoxForge authorization.
13. Scheduler/farm logic must depend on FoxForge capabilities and durable application state, never directly on vendor transports.

## Hardware/deployment validation boundary

Automated gates validate code, packaging and browser behavior but do not replace physical testing.

### Bambu X2D

Record real-device evidence for connection/reconnect, state synchronization, MQTT and FTPS certificate behavior, project delivery, print-start acknowledgement, pause/resume/cancel, lifecycle completion and ambiguous-outcome reconciliation.

### Moonraker/OpenKE

Record real-device evidence for HTTP/WebSocket connectivity, actual endpoint-policy compatibility, upload/checksum/start, pause/resume/cancel and lifecycle completion/failure handling.

### Raspberry Pi 5 / Umbrel

Record installation/restart/persistence, X2D/OpenKE reachability from the actual Umbrel network, authenticated write behavior through the real proxy boundary, upgrades and representative SSE reconnect/resync behavior.

Until these matrices are recorded, documentation must not describe the transports or full deployment as production-validated.

## Automatic filament accounting freeze

P3 is **not the current active implementation priority**. Its partially implemented work is intentionally preserved in draft PR #58 so it can be resumed without losing design effort.

The canonical frozen-state record is [P3 automatic filament accounting — frozen implementation state](status/p3-frozen-state-2026-09-04.md).

P3 may resume only after its documented gate is satisfied. At minimum:

- applicable stabilization findings have repository evidence;
- representative X2D, Moonraker/OpenKE and Raspberry Pi/Umbrel validation is recorded where required;
- the normal inventory UI can create, correct, move, assign, unassign, archive and inspect history/reconciliation state;
- PR #58 is synchronized with the then-current `main` without discarding remediation work;
- backend Python 3.12/3.13, coverage floor, frontend TypeScript/Vitest/build, production-container browser acceptance, unified-container smoke and security gates are green on the exact final P3 head;
- P3 design/status/changelog documentation is synchronized before merge.

## Current development order

1. **Physical/deployment validation:** X2D, Moonraker/OpenKE and Raspberry Pi/Umbrel, including remaining AUD-003/AUD-004/AUD-013 evidence.
2. **Inventory operator workflow:** finish the normal create/correct/move/assign/unassign/archive/history/reconciliation UX above the already guarded inventory API.
3. **Audit closure/documentation:** record the validation evidence and keep README/status/deployment claims aligned with what was actually tested.
4. **Resume P3 only after the gate:** synchronize draft PR #58 with current `main`, finish tests/docs and merge only on exact-head green evidence.
5. **Farm/deep-vendor expansion:** persistent scheduler/farm semantics and deeper Bambu features follow after the preceding foundations are stable.

This order supersedes the older current-status wording that placed P3 immediately after P2. Historical alpha release notes are not changed.

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
- final-image HIGH/CRITICAL vulnerability scanning.

Physical validation remains a separate requirement wherever a finding or production claim depends on real printer/proxy behavior.

## Key documents

- [Independent audit](audits/2026-09-04-independent-project-audit.md)
- [Audit remediation tracker](audits/2026-09-04-remediation-tracker.md)
- [P3 frozen state / resume gate](status/p3-frozen-state-2026-09-04.md)
- [ADR 0001 — PrinterAdapter architecture](adr/0001-printer-adapter-architecture.md)
- [ADR 0005 — browser/deployment trust](adr/0005-browser-deployment-trust.md)
- [Bambu LAN transport](design/bambu-lan-transport.md)
- [Bambu certificate trust](design/bambu-certificate-trust.md)
- [Moonraker transport](design/moonraker-http-transport.md)
- [Secret storage](design/secret-storage.md)
- [Persistence migrations](design/persistence-migrations.md)
- [Inventory atomicity](design/inventory-atomicity.md)
- [Realtime application events](design/realtime-events.md)
- [Coverage policy](testing/coverage-policy.md)

## Release readiness

FoxForge is suitable for continued alpha development and controlled testing. It is **not yet production-ready** and a new versioned release must not be represented as physically validated until the remaining printer/deployment matrices are complete and the release gate is run on the exact frozen release candidate.
