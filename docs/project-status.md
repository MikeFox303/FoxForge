# FoxForge project status

**Snapshot date:** 2026-09-09  
**Canonical branch:** `main`  
**Canonical `main` at start of C6-10:** `0e07a61659cbf356db5cc66f44aa1de91ff0cf3a`  
**Latest semantic pre-release:** `v0.1.0-alpha.4.3`  
**Target release:** `v0.1.0-alpha.5`  
**Active milestone:** Pre-Alpha 5 / Bambu Lab connection and control ([#115](https://github.com/MikeFox303/FoxForge/issues/115))  
**Replacement validation track:** Candidate 6 stabilization ([#154](https://github.com/MikeFox303/FoxForge/issues/154))  
**Current phase:** C6-10 non-publishing software gate  
**Physical Candidate 6 validation:** **not started**  
**Maturity:** runnable/installable alpha; not production-ready

This page is the concise current-state snapshot. Git history, ADRs and design documents remain the durable source of truth. `release/` and dated physical-evidence records are immutable history and must not be rewritten to make an older candidate look current.

## Release and validation state

FoxForge has **not** published final `v0.1.0-alpha.5`.

The latest semantic GitHub pre-release remains **`v0.1.0-alpha.4.3`**.

Candidate 5 is now **historical/failed for Alpha 5 acceptance**. Real X2D testing found two compatibility gaps that required application changes:

- valid X2D `push_status` can arrive without `gcode_state`;
- dual external X2/H2 inventory arrives through `print.vir_slot`, which must take precedence over the legacy `vt_tray` path.

Those defects were fixed by #152/#153 and locked by Candidate 6 regression coverage. Candidate 5 evidence is therefore not Candidate 6 evidence.

Candidate 6 itself is **not published yet**. No Candidate 6 source/image/package identity exists until C6-11, so no physical Candidate 6 PASS can legitimately be claimed before then.

The currently installable Umbrel package remains historical Candidate 5:

```text
Umbrel package: 0.1.0-alpha.4.3-umbrel.5
Candidate 5 source: 0351c659f2d2845fb83bc0b1802c4d9ebeeef1f2
exact image: ghcr.io/mikefox303/foxforge:sha-0351c65@sha256:00c699effbe9b245a4916a8c301df5b67435d75dd42fad02cc5bbf0ca51aec39
target release recorded by package: 0.1.0-alpha.5
```

It remains available for continuity/diagnostics, but it is **not the replacement acceptance target**.

## Candidate 6 software integration state

C6-01 through C6-09 are integrated on `main`.

| Item | State | Durable result |
| --- | --- | --- |
| C6-01 | Integrated | #155 — sanitized physical-derived X2D regression lock. |
| C6-02 | Integrated | #156 — shared Bambu LAN/incremental report classifier cleanup. |
| C6-03 | Integrated | #162 + #178 — `foxforge.thermal_telemetry` v1, Bambu/X2/H2 thermal, Moonraker dynamic heater discovery, sparse-target preservation and malformed/non-finite hardening. |
| C6-04 | Integrated | #157/#163 — Material System UI 2.0. |
| C6-05 | Integrated | #159/#164 — Printer cards / Printer Detail cleanup. |
| C6-06 | Integrated | #160 — staged Add Printer decomposition. |
| C6-07 | Integrated | #158/#161 — diagnostics + memory-only Operator Access cleanup. |
| C6-08 | Integrated | #166 — UI primitives/i18n/code-quality closure. |
| C6-09 | Integrated | #167 — backend architecture/lifecycle guards. |
| C6-10 | **Active** | exact non-publishing software release gate. |
| C6-11 | Blocked | immutable Candidate 6 publication/package identity; only after exact-main C6-10 PASS. |

The C6-10 contract is documented in [`testing/pre-alpha-5-candidate6-software-gate.md`](testing/pre-alpha-5-candidate6-software-gate.md).

## P3 automatic filament accounting

Historical PR #58 is:

- closed;
- not merged;
- archive/reference only;
- not a source that may be rebased/merged wholesale.

P3 was reconstructed on the current architecture and integrated through:

- #165 — R1 durable reservation core;
- #168 — R2 idempotent planning/settlement;
- #169 — R3 fail-closed queue pre-dispatch gate;
- #170 — R4a guarded API/runtime lifecycle;
- #171 — R4b queue operator accounting UI;
- #172 — R5 provider-scoped Candidate 6 validation gate.

Preserved accounting invariants:

- exact `Decimal` mass;
- no overcommit;
- explicit physical-slot → FoxForge-spool assignment;
- accounting/routing guard after fresh routing validation and before any external print side effect;
- idempotent completed settlement;
- no release after a possible print side effect;
- `INDETERMINATE` retains reservations;
- started FAILED/CANCELLED with unknown usage require reconciliation;
- explicit actual-mass reconciliation;
- restart-safe SQLite persistence;
- no consumption guessing from progress;
- vendor-independent accounting contracts with provider-specific enablement composed at runtime.

P3 is therefore **software-integrated**, but it is not yet part of a published Candidate 6 or a physical acceptance claim.

## Dependency/toolchain closure

The Candidate 6 dependency backlog is closed. Relevant integrated updates:

- #173 — backend development tooling;
- #174 — GitHub Actions;
- #175 — i18next/react-i18next;
- #176 — Vitest 4;
- #177 — TypeScript 7.

Superseded Dependabot PRs remain resolved and must not be reopened without a new technical reason.

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, snapshots/events/errors and typed capabilities. |
| Bambu adapter | Functional alpha | Deep MQTT/FTPS/material/routing/control behavior; Candidate 6 physical validation not started. |
| Bambu discovery | Implemented foundation | Bounded server-visible RFC1918 discovery plus manual fallback; authenticated preflight remains authoritative. |
| Bambu Add/Update Printer | Implemented | Provider → Connection → Identity → Verify; test-before-save and rollback-safe replacement. |
| Moonraker adapter | Functional alpha | HTTP/WebSocket/control + common thermal telemetry foundation; physical OpenKE validation pending. |
| Common thermal telemetry | Integrated | `foxforge.thermal_telemetry` v1; Bambu and Moonraker implementations. |
| Fleet/reconnect | Implemented foundation | Dynamic composition, bounded backoff/jitter and secret-safe diagnostics. |
| Durable print queue | Implemented foundation | SQLite dispatch/retry/reconciliation, immutable 3MF inspection, explicit material intent and fail-closed routing. |
| Artifact staging | Implemented | Content-addressed staging, quota/min-free reserve and safe GC. |
| Filament/spool inventory | Implemented | Exact `Decimal` ledger and normal operator workflows. |
| Automatic filament accounting | Software integrated | P3 R1–R5 integrated; publication/physical validation pending. |
| Command security | Implemented foundation | Explicit bearer auth, fail-closed read-only mode, normalized errors and idempotency. |
| Printer credentials | Implemented | SecretStore separates printer credentials from ordinary config/read models. |
| Pause/Resume/Cancel | Implemented | Exact observed vendor-job guard; physical validation pending. |
| Realtime events | Implemented | SSE invalidation/replay with canonical HTTP snapshots. |
| Web UI | Functional alpha | Material System UI 2.0, capability-driven printer detail, staged setup, queue/inventory/accounting and memory-only Operator Access. |
| Docker/ARM64 | C6-10 validation active | Candidate 6 local `amd64` + QEMU `arm64` build/runtime gate; no Candidate 6 image push. |
| Umbrel | Candidate 5 package still installable | C6-10 checks only structural/bootstrap invariants; Candidate 6 identity belongs to C6-11. |
| Persistent farm scheduler | Not implemented | Deferred until printer/deployment/accounting foundations are stable. |

## C6-10 acceptance contract

C6-10 is deliberately **non-publishing**. It must validate the exact source without creating Candidate 6 release side effects.

Required exact-source checks:

1. Backend on Python 3.12 and 3.13: Ruff lint, Ruff format and full pytest/contracts.
2. Frontend: frozen `package-lock`, TypeScript typecheck, Vitest and production Vite build.
3. Browser: locally built production image, Chromium/Playwright acceptance and no public source maps.
4. Security: production npm audit, frozen Python graph audit and high/critical final-image scan.
5. Auth: no token fails closed, correct token enables writes, wrong token is rejected, reverse-proxy identity headers are not an app principal, unsafe trusted-browser mode is rejected.
6. Architecture runtime smoke: local `linux/amd64` and `linux/arm64`; arm64 uses QEMU; no image push.
7. Umbrel structural compatibility only:
   - App Proxy remains present;
   - no host networking;
   - no privileged mode;
   - no `docker.sock`;
   - `${APP_PASSWORD}` → `FOXFORGE_COMMAND_TOKEN`;
   - `${APP_DATA_DIR}/data:/data`;
   - `/healthz`;
   - package role remains `pre-alpha-5-validation-candidate` targeting `0.1.0-alpha.5`.
8. PR closure:
   - during the C6-10 PR, no other open FoxForge PR may exist;
   - after merge to `main`, open PR count must be zero.

The workflow must use the exact PR head when running in pull-request context and the exact merged `main` SHA after merge. The C6-10 branch must be 0 behind before final validation/merge.

C6-10 must **not** update `release/manifest.json`, tag a release, log in/push to GHCR, create a GitHub pre-release or mutate the companion Umbrel Store.

## C6-11 and physical validation

Only after C6-10 passes on the exact merged `main` with open PR count zero may C6-11:

1. freeze the exact FoxForge source SHA;
2. publish matching `linux/amd64` + `linux/arm64` OCI image(s);
3. record the immutable image digest;
4. create the matching Candidate 6 Umbrel package;
5. update the companion Store and run its exact package identity/runtime tests;
6. synchronize README/project status/physical runbook to the single Candidate 6 identity.

After C6-11, the real no-print gate must run on **Raspberry Pi 5 + Umbrel + X2D + AMS 2 Pro** through the normal App Proxy/network path, without host-network workarounds.

Required no-print observations include GUI Operator Access, memory-only credentials, discovery/Add Printer, Verify→change→re-Verify, negative setup cases, rollback-safe Update, restart, network-loss recovery, secret-safe diagnostics, partial initial `push_status`, thermal telemetry, AMS A1–A4 PETG, External Left empty, External Right PLA, and typed left/right topology.

Only after full no-print PASS may the first-print gate run:

`SHA256 → stage → inspect 3MF → selected plate → explicit material bindings → routing compiler → queue → explicit Start → FTPS → project_file`.

The real first-print evidence must preserve compiler-owned `ams_mapping`, `ams_mapping2` and `nozzle_mapping`, exactly one intended Start, stable observed job identity and fail-closed handling of ambiguous remote side effects.

Any application-code change during physical Candidate 6 validation requires a new candidate. Evidence cannot be carried to a changed digest.

## Architecture and safety invariants

- common/domain/application code does not import vendor transports;
- vendor-independent abstractions must not collapse deep Bambu behavior into a lowest-common-denominator model;
- generic frontend code consumes FoxForge contracts/capabilities, not raw Bambu fields or `model == "X2D"` switches;
- unknown/ambiguous physical IDs fail closed;
- ambiguous remote side effects are never blindly retried;
- Operator Access credentials remain memory-only in the browser;
- Docker, ARM64 and Umbrel remain first-class deployment targets;
- durable project state belongs in Git/docs, not chat memory;
- copied/derived upstream code requires explicit copyright/license/provenance notices, while newly written FoxForge code informed by upstream behavior is preferred.

## Key current documents

- [Candidate 6 software gate](testing/pre-alpha-5-candidate6-software-gate.md)
- [Pre-Alpha 5 physical-validation history/runbook](testing/pre-alpha-5-bambu-physical-validation.md)
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
