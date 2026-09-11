# Pre-Alpha 5 Bambu physical validation

- **Target milestone:** `v0.1.0-alpha.5`
- **Tracking:** [#115](https://github.com/MikeFox303/FoxForge/issues/115), [#154](https://github.com/MikeFox303/FoxForge/issues/154)
- **Status:** Candidate 7 immutable package published; no-print physical validation authorized
- **Updated:** 2026-09-11

This is the milestone-specific source of truth for the Bambu/X2D Alpha 5 physical gate. Generic evidence rules remain in [physical-validation-runbook.md](physical-validation-runbook.md) and [physical-evidence-gate.md](physical-evidence-gate.md).

## Active immutable Candidate 7 identity

Candidate 7 is the current **replacement physical-validation candidate inside Pre-Alpha 5**. It is not a semantic Alpha 7 and it is not final `v0.1.0-alpha.5`.

```text
FoxForge application source: 4f769ca89d466d2cbe41360848b6343ec5a8eb36
image tag: ghcr.io/mikefox303/foxforge:sha-4f769ca
OCI digest: sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
exact image: ghcr.io/mikefox303/foxforge:sha-4f769ca@sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.7
Umbrel Store commit: 6e69e4005ae9529eeee5c376c8769393b056ee0d
target semantic release: v0.1.0-alpha.5
```

The Candidate 7 publication recovery run `34630673497` verified the existing immutable OCI index and independent anonymous pulls for both `linux/amd64` and `linux/arm64`. The companion Store PR #39 then passed its package contract, App Password bootstrap, public runtime smoke for both architectures, upstream-version audit and Store Release Gate before merge.

Documentation commits after this identity was frozen are **not application identity**. Physical evidence must name the application source, OCI digest, package version and Store commit above.

## Historical candidates and evidence boundary

Candidate 5 is historical. Real X2D testing exposed partial initial `push_status` and dual-external `vir_slot` compatibility gaps; those findings were fixed before Candidate 6.

Candidate 6 is also historical and **failed the physical Add Printer gate**. On the real X2D, the same payload could pass UI Verify and then fail during Add with a normalized internal adapter error. PR #184 fixed two lifecycle defects:

- Add no longer opens a disposable backend preflight connection immediately before the real live connection; the live fleet adapter performs the single backend-authoritative Add connection before persistence;
- Bambu MQTT uses a short per-session client ID rather than reusing one serial-derived client ID across Verify/Add/reconnect sessions.

Candidate 6 evidence must not be relabeled as Candidate 7 evidence. The Candidate 6 Add failure itself remains useful historical regression evidence, but Candidate 7 must repeat the affected physical path from a clean install/update.

**If application code, the published OCI image, or the Umbrel package definition changes after Candidate 7 evidence begins, stop and publish Candidate 8.** Do not edit Compose in place and reuse Candidate 7 evidence.

## Target environment

Primary acceptance target:

- Raspberry Pi 5 + UmbrelOS;
- `my3d-foxforge 0.1.0-alpha.4.3-umbrel.7` installed from Store commit `6e69e4005ae9529eeee5c376c8769393b056ee0d`;
- Bambu Lab X2D reachable from the normal FoxForge container network namespace;
- AMS 2 Pro connected to the X2D;
- browser access through the normal Umbrel App Proxy path;
- no host-network workaround, privileged mode, Docker socket or manually edited package definition.

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

Every evidence set must record the exact Candidate 7 source, OCI digest, Umbrel package and Store commit. Record PASS/FAIL, date/time and any redacted screenshots/log excerpts needed to explain failures.

# No-print physical gate

Sections 1–7 must pass on the exact Candidate 7 package **without starting a physical print**. Do not proceed to the first real print until every no-print section is green.

## 1. Install and identity

1. Refresh the Community Store.
2. Confirm `my3d-foxforge 0.1.0-alpha.4.3-umbrel.7` is offered.
3. Install/update without editing the published package definition.
4. Confirm `/healthz` succeeds through the normal app path.
5. Record source `4f769ca89d466d2cbe41360848b6343ec5a8eb36`, image digest `sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7`, package `.7` and Store commit `6e69e4005ae9529eeee5c376c8769393b056ee0d` in the private run notes.
6. Confirm ordinary Umbrel App Proxy and bridge/proxy networking are used.

**Pass:** the exact Candidate 7 package starts normally on Raspberry Pi 5/Umbrel and the recorded identity matches this document.

## 2. GUI-only Operator Access

1. Obtain the FoxForge app credential from the Umbrel UI.
2. Open FoxForge through Umbrel.
3. Use **Operator Access / Unlock writes**.
4. Execute a protected low-risk action.
5. Reload the page and verify write access is lost.
6. Verify missing/incorrect credentials fail closed.

**Pass:** no terminal lookup is required and the browser credential remains memory-only.

## 3. Bambu discovery and Add Printer — Candidate 6 blocker regression

This section is the first mandatory Candidate 7 regression. It must prove the real Candidate 6 blocker is gone.

1. Open **Add Printer → Bambu Lab** and confirm **Provider → Connection → Identity → Verify**.
2. Confirm suggested networks, if present, are bounded private RFC1918 networks.
3. Select a sensible suggestion or enter the actual private CIDR manually.
4. Run discovery and verify results remain candidates only.
5. Enter/confirm X2D identity and connection data, then **Verify the exact current payload**.
6. Confirm Verify succeeds.
7. Without changing host/serial/access code/model, immediately press **Add/Save**.
8. Confirm the X2D is persisted and remains connected; **`internal_adapter_error` must not recur**.
9. Confirm the Add path creates one backend-authoritative live connection rather than a disposable Add preflight followed by another live connection.
10. Remove/re-add only if needed by the controlled test procedure; do not create duplicate durable printers.
11. Separately repeat the verification invalidation check: after successful Verify, change host/access-code/model/identity input and confirm Save disables immediately; restore the correct value, Verify again, and confirm Save becomes available only after the new verification succeeds.

Negative cases:

- unreachable/wrong host;
- wrong LAN access code;
- wrong serial number;
- modifying any verified payload field without re-verifying.

**Pass:** Verify → Add succeeds on the real X2D with no internal adapter error, discovery never bypasses authenticated verification, and failed Add leaves no dead configured printer.

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
- metadata-only `push_status` does not falsely satisfy setup;
- Printer Detail/card thermal telemetry shows typed common hotend/bed/chamber data when reported;
- no raw Bambu wire field names leak into common UI/read models;
- stale telemetry is visibly non-authoritative.

**Pass:** Candidate 7 preserves the real-device partial-status behavior fixed after Candidate 5 and exposes common telemetry without vendor leakage.

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
8. Require the immutable Candidate 7 package to report:

```json
{
  "mode": "bambu-validation",
  "enforcedAdapterKinds": ["bambu"]
}
```

**Pass:** reconnect is automatic/secret-safe and the active accounting enforcement mode is explicitly proven from the exact package.

## No-print gate decision

Record PASS/FAIL for sections 1–7 using the same Candidate 7 identity.

**GO to first print only if every no-print section passes.**

If application code, image or package definition changes, stop and publish Candidate 8 before collecting replacement evidence.

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

Repository-safe evidence must include exact Candidate 7 identities, validation date, PASS/FAIL per section, normalized errors/reconnect categories, thermal/material/topology observations, accounting mode, print-plan/binding/reservation facts, dispatch identity, physical start count, estimate/measured usage comparison and redacted screenshots/log excerpts where useful.

Before final `v0.1.0-alpha.5` acceptance:

| Gate | Required result |
| --- | --- |
| Candidate 7 identity | exact source/image/Umbrel package/Store commit recorded |
| Umbrel install/update | exact `.7` package starts on Raspberry Pi 5 |
| Operator credential | visible via Umbrel UI and memory-only in browser |
| Add regression | real X2D Verify → Add succeeds without Candidate 6 `internal_adapter_error` |
| Add/Update safety | exact-payload Verify, fail-before-persist, rollback and terminal replay proven |
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
| Regression | frozen source software gate + Candidate 7 publication + Store package/runtime gates green |

Only after the complete matrix passes:

1. update/close #115 and #154 with evidence references;
2. record the accepted `v0.1.0-alpha.5` release identity/notes;
3. run final release publication gates as required;
4. publish/label the accepted immutable Alpha 5 artifacts without silently changing the validated application/package identity;
5. begin Moonraker physical validation and later provider-specific accounting enablement separately.
