# FoxForge project status

**Snapshot date:** 2026-09-11  
**Canonical branch:** `main`  
**Latest semantic pre-release:** `v0.1.0-alpha.4.3`  
**Target release:** `v0.1.0-alpha.5`  
**Active milestone:** Pre-Alpha 5 / Bambu Lab connection and control ([#115](https://github.com/MikeFox303/FoxForge/issues/115))  
**Replacement validation track:** Candidate stabilization ([#154](https://github.com/MikeFox303/FoxForge/issues/154))  
**Current phase:** Candidate 7 real Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro physical validation  
**Physical Candidate 7 validation:** **authorized; not yet accepted**  
**Maturity:** runnable/installable alpha; not production-ready

This page is the concise current-state snapshot. Git history, ADRs and design documents remain the durable source of truth. `release/` and dated physical-evidence records are immutable history and must not be rewritten to make an older candidate look current.

## Release and validation state

FoxForge has **not** published final `v0.1.0-alpha.5`. The latest semantic GitHub pre-release remains **`v0.1.0-alpha.4.3`**.

The active physical-validation target is Candidate 7:

```text
FoxForge application source: 4f769ca89d466d2cbe41360848b6343ec5a8eb36
image tag: ghcr.io/mikefox303/foxforge:sha-4f769ca
OCI digest: sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
exact image: ghcr.io/mikefox303/foxforge:sha-4f769ca@sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.7
Umbrel Store commit: 6e69e4005ae9529eeee5c376c8769393b056ee0d
target semantic release: v0.1.0-alpha.5
```

Candidate 7 publication recovery run `34630673497` verified the immutable OCI index and independent anonymous pulls for both `linux/amd64` and `linux/arm64`. Companion Store PR #39 passed the FoxForge package contract, App Password bootstrap, public runtime smoke on both architectures, upstream-version audit and Store Release Gate before merge.

Documentation commits after the frozen application source are not application identity. Physical evidence must continue to name source `4f769ca89d466d2cbe41360848b6343ec5a8eb36`, the exact OCI digest, package `.7` and Store commit above.

## Candidate history and why Candidate 7 exists

Candidate 5 is historical/failed for Alpha 5 acceptance. Real X2D testing exposed two compatibility gaps:

- valid X2D `push_status` can arrive without `gcode_state`;
- dual external X2/H2 inventory arrives through `print.vir_slot`, which must take precedence over the legacy `vt_tray` path.

Those defects were fixed and locked before Candidate 6.

Candidate 6 is also historical/failed for physical acceptance. On the real X2D, the same setup payload could pass UI Verify and then fail during Add Printer with the normalized `internal_adapter_error`. PR #184 corrected the connection lifecycle:

- `RuntimePrinterManager.add()` now uses the exact live fleet adapter as the single backend-authoritative Add connection before durable persistence, rather than a disposable Add preflight followed immediately by a second connection;
- Bambu MQTT sessions use short per-session client IDs, preventing Verify/Add/reconnect sessions from intentionally reusing one serial-derived broker identity;
- unexpected adapter exceptions are logged server-side while public setup errors remain sanitized;
- Update Printer retains its separate preflight and rollback because it protects an already-known-good configuration.

Because application code changed after Candidate 6 publication, Candidate 6 evidence could not be reused. Candidate 7 is the required immutable replacement. Candidate 5/6 evidence remains historical and must not be relabeled.

## Candidate 7 software/publication state

The legacy full CI workflow is still named **`Candidate 6 software gate`** for audit continuity. It was rerun against the exact Candidate 7 frozen source `4f769ca89d466d2cbe41360848b6343ec5a8eb36` and completed successfully in run `34616523326`.

The accepted matrix covered:

1. backend Ruff + complete pytest on Python 3.12 and 3.13;
2. frontend frozen-lock install, typecheck, unit tests and production build;
3. Playwright browser acceptance against the exact-source production image;
4. production dependency audit and final-image high/critical vulnerability scan;
5. deployment authentication invariants;
6. runtime smoke for `linux/amd64` and `linux/arm64`;
7. Umbrel structural/bootstrap compatibility;
8. clean milestone closure with no competing FoxForge PRs at freeze time.

Publication then used the dedicated Candidate 7 workflow. The first run successfully created the immutable multi-architecture image but exposed a CI verification bug caused by sequential platform pulls into one local Docker daemon. The publisher was hardened on the publication branch without changing the frozen application source; recovery run `34630673497` verified the already-published exact digest using separate fresh runners for amd64 and arm64 and recorded the publication identity artifact.

The companion Store package is now merged and installable as `.7`; it pins the exact digest and intentionally sets:

```text
FOXFORGE_FILAMENT_ACCOUNTING_MODE=bambu-validation
```

This mode applies the common accounting pre-dispatch gate only to configured Bambu adapters. Moonraker/Klipper accounting remains outside this validation mode.

## P3 automatic filament accounting

Historical PR #58 remains closed/unmerged and is archive/reference only. P3 was reconstructed on the current architecture through R1–R5:

- #165 — durable reservation core;
- #168 — idempotent planning/settlement;
- #169 — fail-closed queue pre-dispatch gate;
- #170 — guarded API/runtime lifecycle;
- #171 — queue operator accounting UI;
- #172 — provider-scoped Bambu validation gate.

Preserved accounting invariants:

- exact `Decimal` mass;
- no overcommit;
- explicit physical-slot → FoxForge-spool assignment;
- accounting/routing guard after fresh routing validation and before external print side effects;
- idempotent completed settlement;
- no release after a possible print side effect;
- `INDETERMINATE` retains reservations;
- started FAILED/CANCELLED with unknown usage require reconciliation;
- explicit actual-mass reconciliation;
- restart-safe SQLite persistence;
- no consumption guessing from progress;
- vendor-independent accounting contracts with provider-specific enablement composed at runtime.

P3 is software-integrated but still requires Candidate 7 physical evidence before Alpha 5 acceptance.

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, snapshots/events/errors and typed capabilities. |
| Bambu adapter | Functional alpha | Deep MQTT/FTPS/material/routing/control behavior; Candidate 7 physical validation now active. |
| Bambu discovery | Implemented foundation | Bounded server-visible RFC1918 discovery plus manual fallback; authenticated verification remains required. |
| Bambu Add Printer | Candidate 7 regression pending | Staged exact-payload Verify plus one backend-authoritative live Add connection before persistence. |
| Bambu Update Printer | Implemented | Separate preflight and rollback preserve known-good configuration. |
| Moonraker adapter | Functional alpha | HTTP/WebSocket/control + common thermal telemetry foundation; physical OpenKE validation pending. |
| Common thermal telemetry | Integrated | `foxforge.thermal_telemetry` v1; Bambu and Moonraker implementations. |
| Material topology | Integrated | AMS/external sources plus typed fixed/dynamic/unknown/stale routes. |
| Fleet/reconnect | Implemented foundation | Dynamic composition, bounded backoff/jitter and secret-safe diagnostics. |
| Durable print queue | Implemented foundation | SQLite dispatch/retry/reconciliation, immutable 3MF inspection, explicit material intent and fail-closed routing. |
| Artifact staging | Implemented | Content-addressed staging, quota/min-free reserve and safe GC. |
| Filament/spool inventory | Implemented | Exact `Decimal` ledger and normal operator workflows. |
| Automatic filament accounting | Candidate 7 validation mode published | Bambu-only physical-validation enforcement; acceptance pending. |
| Command security | Implemented foundation | Explicit bearer auth, fail-closed read-only mode, normalized errors and idempotency. |
| Printer credentials | Implemented | SecretStore separates credentials from ordinary config/read models. |
| Pause/Resume/Cancel | Implemented | Exact observed vendor-job guard; physical validation pending. |
| Realtime events | Implemented | SSE invalidation/replay with canonical HTTP snapshots. |
| Web UI | Functional alpha | Material System UI 2.0, capability-driven printer detail, staged setup, queue/inventory/accounting and memory-only Operator Access. |
| Docker/ARM64 | Candidate 7 published | Immutable amd64/arm64 OCI index and independent anonymous pulls verified. |
| Umbrel | Candidate 7 published | `0.1.0-alpha.4.3-umbrel.7` at Store commit `6e69e4005ae9529eeee5c376c8769393b056ee0d`. |
| Persistent farm scheduler | Not implemented | Deferred until printer/deployment/accounting foundations are physically validated. |

## Active Candidate 7 physical gate

Use [`testing/pre-alpha-5-bambu-physical-validation.md`](testing/pre-alpha-5-bambu-physical-validation.md). Sections 1–7 are the mandatory **no-print** gate on Raspberry Pi 5 + Umbrel + real X2D + AMS 2 Pro.

The first decisive regression is Candidate 6's failed setup path:

```text
exact X2D payload
      ↓
UI Verify succeeds
      ↓
Add / Save immediately
      ↓
printer persists + stays connected
      ↓
NO internal_adapter_error
```

The rest of the no-print gate covers Operator Access, discovery, exact-payload verification invalidation, negative setup cases, rollback-safe Update, restart/reconnect, temporary network loss, sanitized diagnostics, partial X2D initial state, thermal telemetry, AMS A1–A4 PETG, External Left empty, External Right PLA, typed left/right topology and active `bambu-validation` accounting mode.

Only after sections 1–7 all PASS may the first real print gate begin:

`SHA256 → stage → inspect 3MF → selected plate → explicit material bindings → accounting reservation → routing compiler → queue → explicit Start → FTPS → project_file`.

First-print evidence must preserve compiler-owned `ams_mapping`, `ams_mapping2` and `nozzle_mapping`, exactly one physical Start, stable observed vendor-job identity and fail-closed handling of ambiguous remote side effects. Completion evidence must include pre/post measured spool mass and exactly-once settlement/reconciliation behavior.

**Any application code, OCI image or Umbrel package-definition change after Candidate 7 evidence begins requires Candidate 8.** Documentation-only status/evidence commits do not change the frozen application identity.

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

- [Pre-Alpha 5 Candidate 7 physical validation](testing/pre-alpha-5-bambu-physical-validation.md)
- [Legacy Candidate 6 software gate / Candidate 7 exact-source gate](testing/pre-alpha-5-candidate6-software-gate.md)
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
