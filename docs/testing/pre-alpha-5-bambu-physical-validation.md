# Pre-Alpha 5 Bambu physical validation

- **Target milestone:** `v0.1.0-alpha.5`
- **Tracking:** [#115](https://github.com/MikeFox303/FoxForge/issues/115), [#154](https://github.com/MikeFox303/FoxForge/issues/154)
- **Status:** Candidate 6 published; physical validation authorized but not yet completed
- **Updated:** 2026-09-10

This is the milestone-specific source of truth for the Bambu/X2D Alpha 5 physical gate. Generic evidence rules remain in [physical-validation-runbook.md](physical-validation-runbook.md) and [physical-evidence-gate.md](physical-evidence-gate.md).

## Frozen Candidate 6 identity

Candidate 5 is historical and retired for Alpha 5 acceptance. Candidate 1–5 evidence must not be relabeled or carried into Candidate 6.

Candidate 6 is a replacement immutable candidate inside Pre-Alpha 5, not a semantic Alpha 6. C6-10 and C6-11 are complete with this exact identity:

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

Documentation-only commits after application source `78ace6f7...` are not runtime identity changes. Any application-code, image or package-definition change after physical evidence begins invalidates affected evidence and requires a new immutable candidate.

## Target environment

Primary acceptance target:

- Raspberry Pi 5 + UmbrelOS;
- `my3d-foxforge` package `0.1.0-alpha.4.3-umbrel.6` installed from the Community Store;
- ordinary Umbrel App Proxy / bridge networking, **no host-network workaround**;
- Bambu Lab X2D reachable from the FoxForge container network namespace;
- AMS 2 Pro connected to the X2D;
- browser access through the normal Umbrel UI.

Representative material fixture:

```text
X2D
├─ AMS 2 Pro
│  ├─ A1 PETG
│  ├─ A2 PETG
│  ├─ A3 PETG
│  └─ A4 PETG
├─ External Left  -> left toolhead  -> empty
└─ External Right -> right toolhead -> PLA
```

Moonraker/OpenKE remains a separate physical track and does not inherit Bambu accounting evidence.

## Evidence hygiene

Do not commit operator credentials, printer access codes, API keys, cookies, session data, raw private-network targets or unredacted transport exceptions. Use normalized FoxForge error categories and redacted evidence only.

Every evidence set must record the exact Candidate 6 source, immutable OCI digest, Umbrel package and Store commit above.

# No-print physical gate

Sections 1–7 must pass on the exact Candidate 6 package **without starting a physical print**. Do not proceed to the first real print until every no-print section is green.

## 1. Install and identity

1. Refresh the MikeFox303 3D Printing Community Store.
2. Confirm FoxForge package `0.1.0-alpha.4.3-umbrel.6` is offered.
3. Install/update without editing the published package definition.
4. Confirm FoxForge opens through the normal Umbrel path and `/healthz` succeeds.
5. Record package/source/image/digest/Store commit in private run notes.
6. Confirm ordinary App Proxy/bridge networking is used and the package is not host-networked.

**Pass:** Candidate 6 starts normally on Raspberry Pi 5/Umbrel and installed identity matches the frozen C6-11 identity.

## 2. GUI-only Operator Access

1. Obtain the FoxForge app credential from the Umbrel UI; do not use terminal lookup.
2. Open **Operator Access / Unlock writes**.
3. Enter the app password shown by Umbrel.
4. Execute a protected low-risk action.
5. Reload the page and verify write access is lost.
6. Verify missing/incorrect credentials fail closed.

**Pass:** the credential is obtainable through Umbrel UI and remains memory-only in the browser tab.

## 3. Bambu discovery and Add Printer

1. Open **Add Printer → Bambu Lab** and confirm **Provider → Connection → Identity → Verify**.
2. Confirm suggested networks, if present, are bounded private RFC1918 networks; manual CIDR entry remains available.
3. Run discovery and verify results remain candidates only.
4. Enter/confirm the real X2D display/model/serial/host/LAN access code.
5. Verify the exact current payload.
6. Change one verified host/access-code/model/identity field and confirm Save disables immediately.
7. Restore the correct value, re-Verify, then Save.
8. Confirm backend preflight completes before persistence.

Negative cases to record safely: unreachable/wrong host, wrong LAN access code, wrong serial number, and any verified-payload mutation without re-verification.

**Pass:** discovery never bypasses authenticated preflight and failed Add leaves no dead configured printer.

## 4. Safe Update rollback and terminal replay

1. Starting from the known-good X2D, change one connectivity/identity field to an intentionally invalid value.
2. Submit Update and verify preflight rejects the replacement.
3. Confirm the original working configuration remains present/reconnectable.
4. Restore valid settings and verify normal operation.
5. When practical, replay the same terminal failed setup command identity and confirm FoxForge replays the sanitized terminal outcome rather than executing the mutation twice.

**Pass:** invalid replacement data cannot destroy a working configuration and failed setup replay is deterministic/idempotent.

## 5. Live X2D and thermal telemetry

Required observations:

- valid incremental X2D `push_status` with real state-bearing fields can establish state without mandatory `gcode_state`;
- metadata-only `push_status` does not falsely satisfy preflight;
- Printer card/detail expose typed common hotend/bed/chamber telemetry when reported;
- stale telemetry is visibly non-authoritative;
- common read models/UI do not leak raw Bambu wire-field assumptions.

**Pass:** Candidate 6 preserves the physical-derived partial-status regression fix and common thermal telemetry remains typed/fail-safe.

## 6. AMS 2 Pro and material topology

Required observations:

- AMS 2 Pro appears as a four-slot unit;
- A1–A4 report PETG;
- External Left exists and reports empty;
- External Right exists and reports PLA;
- typed topology reports External Left → Left toolhead;
- typed topology reports External Right → Right toolhead;
- `vir_slot` inventory survives incremental updates alongside AMS data;
- route/toolhead presentation comes from `foxforge.material_topology`, not model-name guessing;
- stale/unknown topology is visibly non-authoritative;
- FoxForge inventory spool identity remains separate from printer-reported material state.

**Pass:** UI/topology match the physical fixture and no source/nozzle route is invented from ambiguous evidence.

## 7. Restart, network loss, diagnostics and accounting mode

1. Restart FoxForge and confirm the saved X2D reconnects without being re-added.
2. Reload through Umbrel and confirm Operator Access is locked again.
3. Temporarily make the X2D unreachable using a reversible action.
4. Confirm Diagnostics records a sanitized reconnect incident and bounded retry context.
5. Restore reachability and confirm automatic recovery.
6. Confirm diagnostics expose no access code/credential/raw transport exception.
7. Read `/api/v1/diagnostics/persistence` and record the accounting mode.
8. Require the immutable Candidate 6 package to report:

```json
{
  "mode": "bambu-validation",
  "enforcedAdapterKinds": ["bambu"]
}
```

**Pass:** reconnect is automatic/secret-safe and the published Bambu-only accounting validation mode is explicitly proven.

## No-print gate decision

Record PASS/FAIL for sections 1–7 under the same frozen Candidate 6 identity.

**GO to first print only if every no-print section passes.**

If application code, image or package definition changes, stop and publish a new candidate before collecting replacement evidence.

# First real print and accounting gate

## 8. Immutable 3MF review, explicit routing and reservation

Use a small known-safe X2D `.3mf`. Prefer a single-material PETG print from one known AMS slot for first accounting acceptance so weighed-spool evidence is unambiguous.

1. Select the file and record its SHA-256.
2. Stage it into FoxForge content-addressed storage.
3. Inspect the immutable 3MF print plan and explicitly select the intended plate when needed.
4. Review logical material requirements.
5. Bind every requirement to an explicit currently loaded physical source.
6. Verify missing/stale/incompatible/ambiguous routes are blocked.
7. Verify malformed selected-plate toolhead metadata remains `TOOLHEAD_METADATA_INVALID` and cannot be rescued by a fixed source route.
8. Assign the selected physical source to the exact FoxForge spool used for the test.
9. Weigh/record the spool before print with a reproducible method.
10. Enter the explicit estimated grams and create the durable reservation/accounting plan.
11. Verify the reservation shows the intended physical source, spool and compiler-owned toolhead route.
12. Verify assignment drift after planning blocks dispatch; restore/replan safely rather than bypassing the guard.

Record before Start: artifact SHA-256, selected plate, logical requirements, physical source, toolhead route evidence, spool ID/friendly metadata, starting measured mass, estimated grams, reservation state and any blocker codes.

**Pass:** Start readiness exists only with complete explicit routing and accounting intent.

## 9. Exactly-once physical dispatch

1. Press **Start** as a separate protected action.
2. Verify server-side routing is refreshed immediately before dispatch.
3. Verify Bambu-scoped accounting validation occurs before external print side effects.
4. Verify the reserved spool is still assigned to the same physical source and capacity remains sufficient.
5. Verify FTPS/project storage upload completes.
6. Verify Bambu MQTT `project_file` is accepted.
7. Record the FoxForge dispatch ID and observed vendor job identity/acknowledgement when exposed.
8. Capture sanitized effective `ams_mapping`, `ams_mapping2` and `nozzle_mapping`.
9. Verify external source IDs 254/255 remain `-1` in flat `ams_mapping`, retain real source IDs in `ams_mapping2`, and receive a nozzle only from compiler-owned routing.
10. Verify exactly one intended physical print starts and FoxForge observes the same job/progress.

**Pass:** exactly one physical job starts from the reviewed routing/accounting intent. Any ambiguous remote outcome remains reconciliation-bound and is never blindly retried.

## 10. Completion, measured usage and accounting settlement

Prefer letting the first accounting acceptance print complete normally.

1. Verify the same queue/dispatch identity reaches `COMPLETED`.
2. Verify reservation settlement/debit happens exactly once.
3. Restart/reload FoxForge and confirm the debit is not duplicated.
4. Weigh the same spool after print using the same method.
5. Compute and record measured physical usage from pre/post masses.
6. Record estimated vs measured usage.
7. If correction/reconciliation is required, use the guarded reconciliation workflow with explicit actual grams; never modify SQLite or infer mass from progress.
8. Verify UI/read models reflect final durable state.

**Pass:** settlement is exactly-once and actual-mass evidence is independently measured.

## 11. Guarded job control / uncertain terminal path

A separate small validation may exercise Pause/Resume/Cancel after the normal completion-path test.

1. Against one observed active job, Pause and verify the X2D pauses.
2. Resume and verify the same job resumes.
3. Cancel with explicit confirmation if cancellation is part of the chosen test.
4. Verify stale/incorrect job identity cannot control another job.
5. Verify ambiguous control outcomes are not automatically resent.
6. If a started failed/cancelled job has unknown actual usage, verify accounting becomes reconciliation-required and does not guess/release consumption automatically.

**Pass:** job controls target only the exact observed job and uncertain consumption requires explicit operator reconciliation.

# Alpha 5 acceptance gate

Repository-safe Candidate 6 evidence must include exact source/image/package/Store identities, validation date, PASS/FAIL per section, normalized setup/reconnect outcomes, thermal/material/topology observations, accounting mode, print-plan/binding/reservation facts, dispatch identity, physical start count, estimated/measured usage comparison and redacted screenshots/log excerpts where useful.

Before final `v0.1.0-alpha.5` publication, require:

| Gate | Required result |
| --- | --- |
| Candidate 6 identity | exact source/image/Umbrel package/Store commit recorded |
| Umbrel install/update | exact package starts on Raspberry Pi 5 |
| Operator credential | visible through Umbrel UI and memory-only in browser |
| Add/Update | exact-payload Verify, test-before-save, rollback and deterministic replay proven |
| Discovery | bounded private suggestion/manual CIDR path proven |
| Partial X2D status | state-bearing partial status works; metadata-only remains blocked |
| Reconnect/diagnostics | restart/network-loss recovery and redaction proven |
| Thermal telemetry | typed common readings proven without raw vendor leakage |
| AMS 2 Pro | A1–A4 PETG + Ext-L empty + Ext-R PLA observed |
| Material topology | Ext-L→left and Ext-R→right; stale/unknown fail closed |
| Accounting mode | `bambu-validation` / `bambu` enforcement proven from exact package |
| 3MF parser/routing | selected plate, explicit bindings and invalid-toolhead blockers proven |
| Reservation gate | assignment/capacity checked before external side effects |
| Print dispatch | FTPS/project_file, effective mappings and exactly one physical start |
| Filament settlement | exactly-once debit plus pre/post weighed-spool evidence |
| Job control | guarded Pause/Resume/Cancel or selected completion/control path proven |
| Regression | exact Candidate 6 software/publication/Store gates remain green |

Only after the complete physical matrix passes should #115/#154 be updated for final Alpha 5 acceptance and the semantic `v0.1.0-alpha.5` release process begin. Do not publish final Alpha 5 merely because Candidate 6 is installable.
