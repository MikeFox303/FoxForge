# FoxForge project status

**Snapshot date:** 2026-09-06  
**Canonical branch:** `main`  
**Latest semantic pre-release:** `v0.1.0-alpha.4.3`  
**Active milestone:** Pre-Alpha 5 / Bambu Lab connection and control ([#115](https://github.com/MikeFox303/FoxForge/issues/115))  
**Physical validation:** Candidate 5 published; no-print Raspberry Pi 5/Umbrel/X2D gate pending  
**Maturity:** runnable/installable alpha; not production-ready

This page is the concise current-state snapshot. ADRs/design documents remain normative for architecture. `release/` remains immutable release history, and dated Alpha 4.x status/evidence documents remain historical records.

## Release versus validation candidate

FoxForge has **not** published final `v0.1.0-alpha.5` yet.

The latest semantic GitHub pre-release remains `v0.1.0-alpha.4.3`, released from commit `6845bd1329739c03d766fd86fa8fa308032b1bab`.

The current immutable Pre-Alpha 5 validation target is Candidate 5:

```text
Umbrel package: 0.1.0-alpha.4.3-umbrel.5
candidate source: 0351c659f2d2845fb83bc0b1802c4d9ebeeef1f2
Store commit: 16d57c486ce8e2b26abd5c7e9480188d95f080cb
exact image: ghcr.io/mikefox303/foxforge:sha-0351c65@sha256:00c699effbe9b245a4916a8c301df5b67435d75dd42fad02cc5bbf0ca51aec39
target release: v0.1.0-alpha.5
```

Candidate 5 replaces Candidate 4, which remains **retired for first-print acceptance**. The 2026-09-06 routing audit found that some present-but-invalid 3MF toolhead metadata could be reduced to apparent absence before the compiler saw it. PR #145 closed that fail-closed gap and aligned browser routing review with selected-plate semantics. Candidate 5 also includes the later capability-driven interface refactor and staged Add Printer **Provider → Connection → Identity → Verify** flow through PR #150.

Candidate 5's application source/image is immutable even if documentation-only commits advance `main`. Physical evidence always belongs to the exact application/image digest above. Candidate 1/2/3/4 evidence is historical and cannot be carried into Candidate 5.

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, snapshots/events/errors and typed capabilities. |
| Bambu adapter | Functional alpha | MQTT/TLS state, project storage, material-system/topology observation, fail-closed compiled 3MF routing and common job control; Candidate 5 physical validation pending. |
| Bambu discovery | Implemented foundation | Server-visible RFC1918 suggestions plus explicit manual CIDR scan, bounded `/22` or smaller and candidate-only until normal authenticated setup succeeds. |
| Bambu Add Printer | Implemented | Staged Provider → Connection → Identity → Verify; exact-payload Verify is invalidated by later changes and backend preflight still runs before persistence. |
| Bambu Update Printer | Implemented | Preflight before replacement; failed replacement restores previous durable config, secrets and adapter state. |
| Moonraker adapter | Functional alpha | Production HTTP/WebSocket/control foundation implemented; physical OpenKE validation pending. |
| Fleet management | Implemented | Dynamic composition and normalized lifecycle/events. |
| Reconnect supervision | Implemented foundation | Per-printer workers, bounded concurrency/backoff/jitter and secret-safe diagnostics. |
| Durable print queue | Implemented foundation | SQLite dispatch/retry/reconciliation, immutable 3MF inspection, explicit physical material intent, compiler-owned toolhead routing and explicit `INDETERMINATE`. |
| Artifact staging | Implemented | Content-addressed storage, quota/min-free reserve and safe GC. |
| Filament/spool inventory | Operator workflow implemented | Exact `Decimal` ledger plus create/correct/empty-mass/assignment/archive/history. |
| Command security | Implemented foundation | Explicit bearer auth, permissions, durable idempotency, normalized errors and audit. |
| Printer credentials | Implemented | `SecretStore` separates Bambu access codes and Moonraker API keys from ordinary config. |
| Pause/Resume/Cancel | Implemented | Exact observed vendor-job guard; physical Bambu/Moonraker validation remains. |
| Realtime application events | Implemented | SSE replay/resync invalidation plus canonical HTTP snapshots. |
| Web UI | Functional alpha | Live API, staged setup/discovery, selected-plate 3MF binding review, Material Topology, queue, inventory, capability-driven job control and reconnect diagnostics. |
| Docker/ARM64 | Candidate 5 image published | Linux `amd64` + `arm64` public runtime package smoke passed; physical Raspberry Pi validation remains package-specific. |
| Umbrel | Candidate 5 published | `0.1.0-alpha.4.3-umbrel.5` pins the exact Candidate 5 digest; real no-print deployment gate pending. |
| Automatic filament accounting | **Frozen / not merged** | P3 remains behind physical/deployment gate. |
| Persistent farm scheduler | Not implemented | Deferred until printer/deployment and P3 foundations are stable. |

## Pre-Alpha 5 milestone state

Issue #115 is intentionally Bambu-first. Current Candidate 5 source has closed the main software-side setup/reconnect/routing/interface gaps:

- normalized setup failures instead of raw internal exceptions;
- stable setup identity/model handling;
- conservative discovery plus manual fallback;
- staged Add Printer with exact-current-payload Verify before Save;
- Add and Update test-before-save;
- rollback-safe failed updates;
- durable replay of terminal failed setup requests;
- reconnect diagnostics API/UI;
- live Bambu material-system and typed material-topology foundation;
- immutable 3MF print-plan inspection with a strict missing-versus-invalid toolhead-metadata distinction;
- `TOOLHEAD_METADATA_INVALID` remains a selected-plate blocker even when a physical source has a fixed route;
- explicit source binding and fail-closed compiler-owned toolhead routing;
- selected-plate routing semantics in browser and server;
- adapter-side source/topology revalidation plus Bambu `nozzle_mapping` from the proven compiled route;
- operator-facing Material Topology and 3MF binding review UI;
- capability-driven application shell/printer detail controls;
- GUI-visible Umbrel app password/operator-token path.

What remains before final Alpha 5 is the **real Raspberry Pi 5 + Umbrel + X2D + AMS 2 Pro gate on Candidate 5**: first the complete no-print setup/material-topology/reconnect matrix, then one explicitly reviewed 3MF dispatch and guarded job control.

## Current physical release gate

Use [`testing/pre-alpha-5-bambu-physical-validation.md`](testing/pre-alpha-5-bambu-physical-validation.md) for the exact sequence and Candidate 5 identity.

Required evidence includes:

1. exact Candidate 5 install/update on Raspberry Pi 5/Umbrel;
2. GUI-only Operator Access using the Umbrel-displayed app password and memory-only browser behavior;
3. real staged X2D Add Printer, including Verify→change→re-Verify plus negative host/access-code/serial cases without persistence;
4. safe Update behavior that preserves a working printer after invalid replacement values;
5. restart and network-loss reconnect/recovery with sanitized diagnostics;
6. live X2D state plus AMS 2 Pro/external-source observation and typed topology;
7. selected-plate 3MF review that proves invalid toolhead metadata cannot be masked by a fixed route;
8. real `.3mf` project delivery and exactly-once intended print start only after the no-print gate passes;
9. guarded Pause/Resume/Cancel or completion path against the observed job;
10. secret-safe evidence and no raw credentials/tracebacks.

If implementation changes are required by physical findings, another immutable candidate must be published and affected evidence repeated.

## Audit and P3 state

The immutable audit snapshot remains [`audits/2026-09-04-independent-project-audit.md`](audits/2026-09-04-independent-project-audit.md). Active status is in [`audits/2026-09-04-remediation-tracker.md`](audits/2026-09-04-remediation-tracker.md).

Software-side remediation required before the Candidate 5 physical gate is complete. AUD-003 and AUD-013 remain validation-bound and must not be closed from CI/package evidence alone.

P3 automatic filament accounting remains preserved in its frozen implementation branch/record and does not resume during the Bambu Alpha 5 milestone.

## Development order

1. Run the complete no-print Bambu physical gate on exact Candidate 5.
2. If sections 1–6 pass, run one explicitly reviewed real 3MF print and guarded job control on the same digest.
3. Fix any real-device/deployment defect and publish another immutable candidate if application code changes.
4. Review AUD-003/AUD-013 evidence and update statuses only when the real requirements pass.
5. Prepare and publish final `v0.1.0-alpha.5` only after the exact candidate gate passes.
6. Reassess P3 resume after Alpha 5 stabilization.
7. Continue broader Moonraker physical validation, deep Bambu capabilities and persistent farm scheduling behind the existing typed boundaries.

## Persistence and safety

Persistent `/data` remains sensitive and contains configuration, SQLite state, SecretStore data and staged artifacts. Back up the complete directory before early-alpha upgrades.

Binding invariants include:

- common application/domain code does not depend on vendor transports;
- deep Bambu behavior remains typed and vendor-specific when it is not genuinely common;
- ambiguous remote side effects are not blindly retried;
- realtime events invalidate canonical HTTP state rather than becoming a second source of truth;
- printer credentials are never returned by setup read models;
- browser credentials remain memory-only;
- Docker and Umbrel package the same FoxForge application behavior.

## Key current documents

- [Pre-Alpha 5 Bambu physical validation](testing/pre-alpha-5-bambu-physical-validation.md)
- [Physical evidence gate](testing/physical-evidence-gate.md)
- [Immutable 3MF print-plan inspection](design/immutable-3mf-print-plan.md)
- [Material routing compiler](design/material-routing-compiler.md)
- [Application-managed printer setup](design/app-managed-printer-setup.md)
- [Reconnect supervision](design/reconnect-supervision.md)
- [Bambu LAN transport](design/bambu-lan-transport.md)
- [Deployment authentication](testing/deployment-auth-contract.md)
- [Documentation index](README.md)
