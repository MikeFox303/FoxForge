# FoxForge project status

**Snapshot date:** 2026-09-10  
**Canonical branch:** `main`  
**Latest semantic pre-release:** `v0.1.0-alpha.4.3`  
**Target release:** `v0.1.0-alpha.5` — **not published**  
**Active milestone:** Pre-Alpha 5 / Bambu Lab connection and control ([#115](https://github.com/MikeFox303/FoxForge/issues/115))  
**Replacement validation track:** Candidate 6 ([#154](https://github.com/MikeFox303/FoxForge/issues/154))  
**Current phase:** Candidate 6 physical validation authorized  
**Physical Candidate 6 validation:** **not completed**  
**Maturity:** runnable/installable alpha; not production-ready

This page is the concise current-state snapshot. Git history, ADRs, validation runbooks and immutable package identities remain the durable source of truth. Historical candidate evidence must not be rewritten to look current.

## Candidate 6 immutable identity

C6-10 and C6-11 are complete. The frozen Candidate 6 application/package identity is:

```text
FoxForge application source: 78ace6f7b7412aa0d3fc58bed095aecdf9920f94
C6-10 exact-main gate: run 34439269464 — PASS
image tag: ghcr.io/mikefox303/foxforge:sha-78ace6f
OCI digest: sha256:b01f1d44199a4413167ee2369c0dfbcafa602312442772d27de18e04c24ed0eb
exact image: ghcr.io/mikefox303/foxforge:sha-78ace6f@sha256:b01f1d44199a4413167ee2369c0dfbcafa602312442772d27de18e04c24ed0eb
publication verification: run 34440021792 — PASS
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.6
Umbrel Store PR: MikeFox303/umbrel-3d-printing-store#38
Umbrel Store commit: 018d29a8668e923c7f1a3447fc12273939aefbb8
Store post-merge FoxForge package/runtime gate: run 34509996521 — PASS
Store post-merge release gate: run 34509996582 — PASS
target semantic release: v0.1.0-alpha.5 — not published
```

Documentation-only commits after `78ace6f7...` do not change the Candidate 6 application identity. Any application code, image or package-definition change does.

Candidate 5 remains historical/failed for Alpha 5 acceptance. Real X2D testing found partial initial `push_status` and dual-external `print.vir_slot` compatibility gaps, which were corrected and regression-locked for Candidate 6. Candidate 1–5 evidence cannot be carried into Candidate 6.

## Candidate 6 milestone state

| Item | State | Durable result |
| --- | --- | --- |
| C6-01 | Integrated | #155 — sanitized physical-derived X2D regression lock. |
| C6-02 | Integrated | #156 — shared Bambu LAN/incremental report classifier cleanup. |
| C6-03 | Integrated | #162 + #178 — `foxforge.thermal_telemetry` v1 for Bambu and Moonraker/Klipper. |
| C6-04 | Integrated | #157/#163 — Material System UI 2.0. |
| C6-05 | Integrated | #159/#164 — capability-driven Printer cards / Printer Detail. |
| C6-06 | Integrated | #160 — staged Add Printer Provider → Connection → Identity → Verify. |
| C6-07 | Integrated | #158/#161 — diagnostics + memory-only Operator Access. |
| C6-08 | Integrated | #166 — UI primitives/i18n/code-quality closure. |
| C6-09 | Integrated | #167 — backend architecture/lifecycle guards. |
| C6-10 | **PASS** | Exact frozen source `78ace6f7...`; full software gate run `34439269464`. |
| C6-11 | **PASS** | Multi-arch OCI published/verified; Store Candidate 6 merged as `018d29a8...`; post-merge package/runtime and Store gates PASS. |
| Physical gate | **Next** | Exact Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro no-print gate, then first print/accounting only after no-print PASS. |

## P3 automatic filament accounting

Historical PR #58 is closed/unmerged archive/reference only. P3 was reconstructed on the current architecture and integrated through #165, #168, #169, #170, #171 and #172.

Preserved invariants include exact `Decimal` mass, no overcommit, explicit physical-slot → FoxForge-spool assignment, a fresh-routing pre-dispatch accounting guard before external side effects, idempotent completed settlement, held reservations for `INDETERMINATE`, explicit reconciliation for uncertain started outcomes, restart-safe SQLite persistence and no mass guessing from print progress.

The published Candidate 6 Umbrel package intentionally sets:

```text
FOXFORGE_FILAMENT_ACCOUNTING_MODE=bambu-validation
```

This enables automatic pre-dispatch accounting enforcement only for Bambu adapters. Moonraker/Klipper and unknown providers remain outside the automatic enforcement mode. Physical Bambu accounting acceptance still requires explicit reservation evidence and pre/post measured spool mass.

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, snapshots/events/errors and typed capabilities. |
| Bambu adapter | Functional alpha | Deep MQTT/FTPS/material/routing/control behavior; Candidate 6 physical validation next. |
| Bambu discovery | Implemented foundation | Bounded server-visible RFC1918 discovery plus manual fallback; authenticated preflight authoritative. |
| Bambu Add/Update Printer | Implemented | Staged exact-payload Verify, test-before-save and rollback-safe replacement. |
| Moonraker adapter | Functional alpha | HTTP/WebSocket/control + common thermal telemetry; physical OpenKE validation pending. |
| Common thermal telemetry | Integrated | `foxforge.thermal_telemetry` v1, Bambu + Moonraker implementations. |
| Fleet/reconnect | Implemented foundation | Dynamic composition, bounded backoff/jitter and secret-safe diagnostics. |
| Durable print queue | Implemented foundation | SQLite dispatch/retry/reconciliation, immutable 3MF inspection and fail-closed routing. |
| Artifact staging | Implemented | Content-addressed staging, quota/min-free reserve and safe GC. |
| Filament/spool inventory | Implemented | Exact `Decimal` ledger and operator workflows. |
| Automatic filament accounting | Candidate 6 validation enabled for Bambu | Software integrated; physical weighed-spool acceptance pending. |
| Command security | Implemented foundation | Explicit bearer auth, fail-closed read-only mode, normalized errors and idempotency. |
| Printer credentials | Implemented | SecretStore separates printer credentials from ordinary config/read models. |
| Pause/Resume/Cancel | Implemented | Exact observed vendor-job guard; physical validation pending. |
| Realtime events | Implemented | SSE invalidation/replay with canonical HTTP snapshots. |
| Web UI | Functional alpha | Material System UI 2.0, staged setup, queue/inventory/accounting and memory-only Operator Access. |
| Docker/ARM64 | **Candidate 6 published** | Immutable `amd64`/`arm64` index and public pulls verified. |
| Umbrel | **Candidate 6 installable** | `0.1.0-alpha.4.3-umbrel.6`, Store commit `018d29a8...`, no host networking. |
| Persistent farm scheduler | Not implemented | Deferred until printer/deployment/accounting foundations are physically accepted. |

## Physical Candidate 6 gate

Physical evidence is now authorized against the immutable identity above. The primary target is Raspberry Pi 5 + Umbrel + Bambu X2D + AMS 2 Pro through the ordinary App Proxy/bridge deployment path, without host networking.

The no-print gate must prove GUI Operator Access, memory-only credentials, discovery/Add Printer, exact-payload Verify→change→re-Verify, negative setup cases, rollback-safe Update, restart, network-loss recovery, secret-safe diagnostics, partial initial X2D `push_status`, common thermal telemetry and the real material fixture:

```text
AMS 2 Pro: A1 PETG, A2 PETG, A3 PETG, A4 PETG
External Left: empty -> left toolhead
External Right: PLA -> right toolhead
```

Only after every no-print section passes may the first-print path run:

```text
SHA256 → stage → inspect immutable 3MF → select plate → explicit material bindings
→ routing compiler → accounting reservation → queue → explicit Start
→ FTPS upload → MQTT project_file → exactly one physical job
```

The first-print evidence must preserve compiler-owned `ams_mapping`, `ams_mapping2` and `nozzle_mapping`, exact observed vendor-job identity, fail-closed handling of ambiguous outcomes, and measured spool usage. No consumption may be guessed from print progress.

Any application/image/package-definition change during Candidate 6 physical validation requires a new immutable candidate. Documentation-only status/evidence commits do not change the runtime candidate.

See [`testing/pre-alpha-5-bambu-physical-validation.md`](testing/pre-alpha-5-bambu-physical-validation.md).

## Architecture and safety invariants

- common/domain/application code does not import vendor transports;
- vendor-independent abstractions do not collapse deep Bambu behavior into a lowest-common-denominator model;
- generic frontend code consumes FoxForge contracts/capabilities, not raw Bambu fields or model-name switches;
- unknown/ambiguous physical IDs fail closed;
- ambiguous remote side effects are never blindly retried;
- Operator Access credentials remain memory-only in the browser;
- Docker, ARM64 and Umbrel remain first-class deployment targets;
- copied/derived upstream code requires explicit copyright/license/provenance notices;
- durable project state belongs in Git/docs, not chat memory.

## Key current documents

- [Candidate 6 software gate](testing/pre-alpha-5-candidate6-software-gate.md)
- [Pre-Alpha 5 physical-validation runbook](testing/pre-alpha-5-bambu-physical-validation.md)
- [Physical evidence gate](testing/physical-evidence-gate.md)
- [Thermal telemetry](design/thermal-telemetry.md)
- [Immutable 3MF print-plan inspection](design/immutable-3mf-print-plan.md)
- [Material routing compiler](design/material-routing-compiler.md)
- [Application-managed printer setup](design/app-managed-printer-setup.md)
- [Reconnect supervision](design/reconnect-supervision.md)
- [Bambu LAN transport](design/bambu-lan-transport.md)
- [Moonraker transport](design/moonraker-http-transport.md)
- [Deployment authentication](testing/deployment-auth-contract.md)
- [Documentation index](README.md)
