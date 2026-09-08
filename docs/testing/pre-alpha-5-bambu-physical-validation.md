# Pre-Alpha 5 Bambu physical validation

- **Target milestone:** `v0.1.0-alpha.5`
- **Tracking:** [#115](https://github.com/MikeFox303/FoxForge/issues/115), [#154](https://github.com/MikeFox303/FoxForge/issues/154)
- **Status:** Candidate 6 software stabilization in progress; physical validation not authorized until C6-11 freezes an exact identity
- **Updated:** 2026-09-08

This is the milestone-specific source of truth for the Bambu/X2D Alpha 5 physical gate. Generic evidence rules remain in [physical-validation-runbook.md](physical-validation-runbook.md) and [physical-evidence-gate.md](physical-evidence-gate.md).

## Candidate status

Candidate 5 is historical and retired for Alpha 5 acceptance. Its immutable identity remains useful only as prior evidence context:

```text
FoxForge application source: 0351c659f2d2845fb83bc0b1802c4d9ebeeef1f2
image tag: ghcr.io/mikefox303/foxforge:sha-0351c65
OCI digest: sha256:00c699effbe9b245a4916a8c301df5b67435d75dd42fad02cc5bbf0ca51aec39
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.5
Umbrel Store commit: 16d57c486ce8e2b26abd5c7e9480188d95f080cb
```

Real Candidate 5 X2D validation exposed compatibility gaps in partial initial `push_status` handling and dual external `vir_slot` preservation. Those findings produced the Candidate 6 regression/fix sequence, including PRs #152/#153 and the physical-derived regression lock in #155. Candidate 5 evidence must not be relabeled as Candidate 6 evidence.

Candidate 6 is a **replacement immutable candidate inside Pre-Alpha 5**, not a semantic Alpha 6. Its exact identity does not exist yet. C6-11 must eventually record:

```text
FoxForge application source: <C6_SOURCE_SHA>
image tag: <C6_IMAGE_TAG>
OCI digest: <C6_OCI_DIGEST>
exact image: <C6_IMAGE_TAG>@<C6_OCI_DIGEST>
Umbrel package: <C6_UMBREL_PACKAGE>
Umbrel Store commit: <C6_STORE_COMMIT>
target semantic release: v0.1.0-alpha.5
```

**Do not begin Candidate 6 physical evidence until all placeholders above are replaced by one frozen C6-11 identity.** Any application/image/package-definition change after evidence begins invalidates that evidence and requires Candidate 7.

## Pre-publication software gate

Before C6-11 publishes Candidate 6:

1. C6-01 through C6-09 are integrated on current `main`;
2. P3 R1-R5 software capability is integrated;
3. historical P3 PR #58 is resolved as superseded rather than merged;
4. dependency/toolchain backlog is closed or explicitly superseded by audited integrated updates;
5. C6-10 passes on clean `main` for Python 3.12/3.13, frontend, Browser acceptance, security, deployment auth, amd64/arm64 container and Umbrel package contract;
6. README/status/changelog/runbook describe the same Candidate 6 pre-publication state.

C6-11 then freezes the exact source/image/package identity. Physical validation occurs only afterwards.

## Target environment

Primary acceptance target:

- Raspberry Pi 5 + UmbrelOS;
- `my3d-foxforge` installed from the exact Candidate 6 Community Store package;
- Bambu Lab X2D reachable from the normal FoxForge container network namespace;
- AMS 2 Pro connected to the X2D;
- browser access through the normal Umbrel App Proxy path;
- no host-network workaround.

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

Every evidence set must record the exact Candidate 6 source, immutable OCI digest, Umbrel package and Store commit. Documentation commits are not application identity.

# No-print physical gate

Sections 1–7 must pass on the exact Candidate 6 package **without starting a physical print**. Do not proceed to the first real print until every no-print section is green.

## 1. Install and identity

1. Refresh the Community Store.
2. Confirm the exact Candidate 6 package recorded by C6-11 is offered.
3. Install/update without editing the published package definition after evidence begins.
4. Confirm `/healthz` succeeds through the normal app path.
5. Record source/image/digest/package/Store identities in private run notes.
6. Confirm ordinary Umbrel App Proxy and bridge/proxy networking are used.

**Pass:** the exact Candidate 6 package starts normally on Raspberry Pi 5/Umbrel and its identity matches C6-11.

## 2. GUI-only Operator Access

1. Obtain the FoxForge app credential from the Umbrel UI.
2. Open FoxForge through Umbrel.
3. Use **Operator Access / Unlock writes**.
4. Execute a protected low-risk action.
5. Reload the page and verify write access is lost.
6. Verify missing/incorrect credentials fail closed.

**Pass:** no terminal lookup is required and the browser credential remains memory-only.

## 3. Bambu discovery and Add Printer

1. Open **Add Printer → Bambu Lab** and confirm **Provider → Connection → Identity → Verify**.
2. Confirm suggested networks, if present, are bounded private RFC1918 networks.
3. Select a sensible suggestion or enter the actual private CIDR manually.
4. Run discovery and verify results remain candidates only.
5. Enter/confirm X2D identity and connection data, then Verify the exact current payload.
6. After successful Verify, change host/access-code/model/identity input and confirm Save disables immediately.
7. Restore the correct value, Verify again, and confirm Save becomes available only after the new verification succeeds.
8. Save and confirm persistence happens only after backend authoritative preflight.

Negative cases:

- unreachable/wrong host;
- wrong LAN access code;
- wrong serial number;
- modifying any verified payload field without re-verifying.

**Pass:** discovery never bypasses authenticated preflight and failed Add leaves no dead configured printer.

## 4. Safe Update rollback and terminal replay

Starting from the known-good X2D:

1. change one connectivity/identity field to an intentionally invalid value;
2. submit Update;
3. verify preflight rejects the replacement;
4. confirm the original configuration remains present and reconnectable;
5. restore/use valid settings and confirm normal operation;
6. verify replaying the same terminal failed setup command identity does not execute a second setup attempt.

**Pass:** invalid replacement data cannot destroy a working configuration and terminal failed setup replay is deterministic.

## 5. Live X2D, thermal telemetry and partial initial status

Required observations:

- a valid incremental X2D `push_status` without `gcode_state` can satisfy initial state when it carries real state-bearing fields;
- metadata-only `push_status` does not falsely satisfy preflight;
- Printer Detail/card thermal telemetry shows typed common hotend/bed/chamber data when reported;
- no raw Bambu wire field names leak into common UI/read models;
- stale telemetry is visibly non-authoritative.

**Pass:** current Candidate 6 preserves the real-device partial-status behavior fixed after Candidate 5 and exposes common telemetry without vendor leakage.

## 6. AMS 2 Pro and material topology

Required observations:

- AMS 2 Pro identified as a four-slot unit;
- A1–A4 report PETG;
- External Left exists and reports empty;
- External Right exists and reports PLA;
- topology reports External Left → Left toolhead;
- topology reports External Right → Right toolhead;
- `vir_slot` inventory survives incremental updates alongside AMS data;
- route/toolhead presentation comes from `foxforge.material_topology`, not a model-name guess;
- stale/unknown topology is visibly non-authoritative;
- FoxForge inventory spool identity remains separate from physical printer material state.

**Pass:** material-system and topology UI match the real fixture and no left/right route is invented from ambiguous evidence.

## 7. Restart, network loss, diagnostics and accounting mode

1. Restart FoxForge and verify the saved X2D reconnects automatically.
2. Reload through Umbrel and verify Operator Access remains locked until explicitly unlocked.
3. Temporarily make X2D unreachable with a reversible action.
4. Confirm Diagnostics records a sanitized reconnect incident and normalized retry context.
5. Restore reachability and confirm automatic recovery without re-adding the printer.
6. Confirm credentials/access codes/raw vendor exceptions are absent from diagnostics.
7. Read `/api/v1/diagnostics/persistence` and record `filamentAccounting.mode` plus `enforcedAdapterKinds`.
8. For Candidate 6 accounting validation, require the immutable package to report:

```json
{
  "mode": "bambu-validation",
  "enforcedAdapterKinds": ["bambu"]
}
```

If C6-11 intentionally publishes a package with accounting disabled, do not perform the accounting acceptance portion until a new immutable package identity is published; do not edit the installed package definition in place and reuse evidence.

**Pass:** reconnect is automatic/secret-safe and the active accounting enforcement mode is explicitly proven from the exact package.

## No-print gate decision

Record PASS/FAIL for sections 1–7 using the same Candidate 6 identity.

**GO to first print only if every no-print section passes.**

If application code, image or package definition changes, stop and publish Candidate 7 before collecting replacement evidence.

# First real print and accounting gate

## 8. Immutable 3MF review, explicit routing and reservation intent

Use a small known-safe X2D `.3mf` whose intended plate/materials are understood before the test. Prefer a single-material PETG print from one known AMS slot for the first accounting acceptance so weighed-spool evidence is unambiguous.

Through the browser:

1. select the file;
2. compute/record SHA-256;
3. stage it into FoxForge content-addressed storage;
4. inspect the immutable 3MF print plan;
5. select the intended plate explicitly for multi-plate files;
6. review logical material requirements;
7. bind every required material to an explicit currently loaded physical source;
8. verify missing/stale/incompatible/ambiguous/unknown routes are blocked;
9. verify present-but-invalid toolhead metadata retains `TOOLHEAD_METADATA_INVALID` and cannot fall back to a fixed source route;
10. verify a blocked unselected plate does not poison a different safe selected plate;
11. enqueue without a client-owned `toolheadId`;
12. assign the physical source to the exact FoxForge inventory spool used for the test;
13. weigh/record the spool before print using a reproducible method;
14. enter explicit estimated grams in the Queue accounting panel and create the durable reservation;
15. verify the reservation displays the expected physical source, reserved spool and compiler-owned toolhead evidence;
16. verify changing/removing the slot assignment after planning produces visible assignment drift and blocks dispatch; restore/replan with a new queue entry if needed.

Record before Start:

- artifact SHA-256;
- selected plate;
- logical material requirements;
- selected physical source and toolhead evidence;
- FoxForge spool ID/friendly metadata;
- pre-print measured spool mass;
- explicit estimated grams;
- reservation state;
- any print-plan warning/blocker codes.

**Pass:** the job reaches Start readiness only with complete explicit routing intent and durable accounting evidence.

## 9. Exactly-once physical dispatch

1. press **Start** as a separate protected action;
2. verify fresh server-side material routing/printer assessment;
3. verify provider-scoped accounting validation runs before durable `DISPATCHING`;
4. verify the reserved spool is still assigned to the same physical source and active holds fit current remaining mass;
5. verify FTPS/project storage upload completes;
6. verify Bambu `project_file` is accepted;
7. record dispatch ID and vendor job identity/acknowledgement when exposed;
8. capture effective `ams_mapping`, `ams_mapping2` and `nozzle_mapping` in a secret-safe form;
9. verify external 254/255 stays `-1` in flat `ams_mapping`, retains real source ID in `ams_mapping2`, and obtains a nozzle only from compiler-owned toolhead routing;
10. verify exactly one intended physical print starts;
11. verify FoxForge observes that same active job/progress.

**Pass:** exactly one physical print starts from the reviewed routing/accounting intent. Any ambiguous outcome remains `INDETERMINATE`/reconciliation-bound and is not blindly retried.

## 10. Completion, measured usage and accounting settlement

Prefer allowing the first accounting acceptance print to complete normally.

1. verify the queue reaches `COMPLETED` for the same dispatch/job identity;
2. verify the reservation settles exactly once and the inventory ledger is debited once by the explicit estimate;
3. restart/reload FoxForge and verify the debit is not duplicated;
4. weigh the same spool after print with the same method;
5. compute measured physical usage from pre/post masses;
6. record estimated vs measured usage as evidence;
7. if explicit correction/reconciliation is required by the test procedure, enter measured actual grams through the guarded reconciliation workflow rather than modifying SQLite or guessing from progress;
8. verify realtime UI/read models reflect the final durable state.

**Pass:** settlement is exactly-once and measured evidence is recorded without using printer progress as a mass estimator.

## 11. Guarded job control / uncertain terminal path

A separate small validation may exercise Pause/Resume/Cancel if required after the completion-path accounting test. Against one observed active job:

1. Pause and verify X2D pauses.
2. Resume and verify the same job resumes.
3. Cancel with explicit confirmation if testing cancellation.
4. Verify stale/incorrect job identity cannot control another job.
5. Verify an ambiguous control outcome is not automatically resent.
6. If a started failed/cancelled job has unknown actual usage, verify accounting becomes `reconciliation_required` and retains capacity until explicit actual mass is entered.

**Pass:** controls target only the exact observed job and uncertain consumption never auto-releases or auto-consumes a guessed amount.

## 12. Evidence and Alpha 5 gate

Repository-safe evidence must include exact Candidate 6 identities, validation date, PASS/FAIL per section, normalized errors/reconnect categories, thermal/material/topology observations, accounting mode, print-plan/binding/reservation facts, dispatch identity, physical start count, estimate/measured usage comparison and redacted screenshots/log excerpts where useful.

Before final `v0.1.0-alpha.5` acceptance:

| Gate | Required result |
| --- | --- |
| Candidate 6 identity | exact source/image/Umbrel package/Store commit recorded |
| Umbrel install/update | exact package starts on Raspberry Pi 5 |
| Operator credential | visible via Umbrel UI and memory-only in browser |
| Add/Update | exact-payload Verify, test-before-save, rollback and terminal replay proven |
| Discovery | bounded private suggestion/manual CIDR path proven |
| Partial X2D status | real state without mandatory `gcode_state` proven; metadata-only remains blocked |
| Reconnect/diagnostics | restart/network-loss recovery and redaction proven |
| Thermal telemetry | common typed readings proven without raw Bambu leakage |
| AMS 2 Pro | A1–A4 PETG + Ext-L empty + Ext-R PLA observed |
| Material topology | Ext-L→left and Ext-R→right; stale/unknown fail closed |
| Accounting mode | exact package reports `bambu-validation` / `bambu` for accounting acceptance |
| 3MF parser/routing | selected plate, explicit bindings, `TOOLHEAD_METADATA_INVALID` blocker proven |
| Reservation gate | complete reservation/assignment/capacity checked before `DISPATCHING` |
| Print dispatch | FTPS/project_file, effective mappings, exactly one physical start |
| Filament settlement | exactly-once debit plus pre/post weighed-spool evidence |
| Job control | guarded Pause/Resume/Cancel or completion path proven |
| Regression | exact-head backend/frontend/browser/container/security/ARM64/Umbrel gates green |

Only after the complete matrix passes:

1. update/close #115 and #154 with evidence references;
2. record the accepted `v0.1.0-alpha.5` release identity/notes;
3. run final exact-head/release publication gates as required;
4. publish/label the accepted immutable Alpha 5 artifacts without changing the validated application/package identity;
5. begin Moonraker physical validation and later provider-specific accounting enablement separately.
