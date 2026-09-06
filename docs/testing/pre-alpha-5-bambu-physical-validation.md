# Pre-Alpha 5 Bambu physical validation

- **Target milestone:** `v0.1.0-alpha.5`
- **Tracking:** [#115](https://github.com/MikeFox303/FoxForge/issues/115)
- **Status:** physical validation paused; Candidate 4 retired for first-print acceptance after routing audit
- **Updated:** 2026-09-06

This is the milestone-specific source of truth for the Bambu/X2D Alpha 5 release gate. Generic evidence rules remain in [physical-validation-runbook.md](physical-validation-runbook.md) and [physical-evidence-gate.md](physical-evidence-gate.md).

## Candidate status

Candidate 4 was the canonical validation target before the 2026-09-06 release-readiness routing audit:

```text
FoxForge application source: c11f7145b4354aa79c8f0fad223648240e652bac
image tag: ghcr.io/mikefox303/foxforge:sha-c11f714
OCI digest: sha256:75d656bafcafb4e0e566548f6cca941244d29fef1bbc5be98e425f375246056a
exact image: ghcr.io/mikefox303/foxforge:sha-c11f714@sha256:75d656bafcafb4e0e566548f6cca941244d29fef1bbc5be98e425f375246056a
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.4
Umbrel Store commit: 07b8e8087ac9897d4c2f5dc45944b48dfb0938e1
base semantic release: v0.1.0-alpha.4.3
target semantic release: v0.1.0-alpha.5
```

Candidate 4 is now **retired for the first physical print**. The audit found that some present-but-invalid 3MF toolhead metadata could be reduced to apparent metadata absence before the routing compiler saw it. A fixed physical source route could then mask parser failure. PR #145 closes that gap and aligns browser routing review with selected-plate semantics.

**Do not collect new first-print acceptance evidence on Candidate 4. Do not carry Candidate 1/2/3/4 evidence into a replacement digest.**

The next physical run may begin only after:

1. PR #145 (or its final equivalent) is merged with exact-head software gates green;
2. a new immutable FoxForge source/image is published;
3. the Umbrel Store package pins that exact immutable digest;
4. this document is updated with the new exact source/image/package/Store identities.

## Target environment

Primary acceptance target:

- Raspberry Pi 5 + UmbrelOS;
- `my3d-foxforge` installed from the Community Store;
- Bambu Lab X2D reachable from the FoxForge container network namespace;
- AMS 2 Pro connected to the X2D;
- browser access through the normal Umbrel App Proxy path.

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

Moonraker/OpenKE remains a separate physical track. P3 automatic filament accounting stays frozen during this Bambu milestone.

## Evidence hygiene

Do not commit operator credentials, printer access codes, API keys, cookies, session data or unredacted private network targets. Use normalized FoxForge error categories and redacted evidence only.

Every physical evidence set must record the exact application source, immutable OCI digest and Umbrel Store commit. Documentation commits are not application identity.

# No-print physical gate

Sections 1–6 must pass on one exact replacement candidate **without starting a physical print**. Do not proceed to section 7 until the complete no-print gate is green.

## 1. Install and identity

1. Refresh the Community Store.
2. Confirm the replacement package identity matches this document.
3. Install/update without editing Compose or container settings manually.
4. Confirm `/healthz` succeeds through the normal app path.
5. Record source/image/digest/Store identities in private run notes.
6. Confirm ordinary Umbrel App Proxy and bridge networking are used; do not switch to host networking as a workaround.

**Pass:** the exact replacement package starts normally on Raspberry Pi 5/Umbrel and its identity matches the pinned image.

## 2. GUI-only Operator Access

1. Obtain the FoxForge app credential from the Umbrel UI.
2. Open FoxForge through Umbrel.
3. Use **Operator Access / Unlock writes**.
4. Execute a protected low-risk action.
5. Reload the page and verify write access is lost.
6. Verify missing/incorrect credentials fail closed.

**Pass:** no terminal lookup is required and the browser credential remains memory-only.

## 3. Bambu discovery and Add Printer

1. Open Add Printer → Bambu Lab.
2. Confirm suggested networks, if present, are bounded private RFC1918 networks.
3. Select a sensible suggestion or enter the actual private CIDR manually.
4. Run discovery and verify results remain candidates only.
5. Verify X2D metadata is sensible and Test Connection succeeds with valid configuration.
6. Add the printer and confirm persistence happens only after successful preflight.

Negative cases:

- unreachable/wrong host;
- wrong LAN access code;
- wrong serial number.

**Pass:** discovery never bypasses authenticated preflight, failed Add leaves no dead configured printer, and errors are normalized without raw internal exceptions.

## 4. Safe Update rollback and terminal replay

Starting from the known-good X2D:

1. change one connectivity/identity field to an intentionally invalid value;
2. submit Update;
3. verify preflight rejects the replacement;
4. confirm the original configuration remains present and reconnectable;
5. restore/use valid settings and confirm normal operation;
6. verify replaying the same terminal failed setup command identity does not execute a second setup attempt.

**Pass:** invalid replacement data cannot destroy a working configuration and terminal failed setup replay is deterministic.

## 5. Live X2D, AMS 2 Pro and material topology

Required observations:

- AMS 2 Pro identified as a four-slot unit;
- A1–A4 report PETG;
- External Left exists and reports empty;
- External Right exists and reports PLA;
- topology reports External Left → Left toolhead;
- topology reports External Right → Right toolhead;
- route/toolhead presentation comes from `foxforge.material_topology`, not a model-name guess;
- stale/unknown topology is visibly non-authoritative;
- FoxForge inventory spool identity remains separate from physical printer material state.

**Pass:** material-system and topology UI match the actual fixture and no left/right route is invented from ambiguous evidence.

## 6. Restart, network loss and diagnostics

1. Restart FoxForge and verify the saved X2D reconnects automatically.
2. Reload through Umbrel and verify Operator Access remains locked until explicitly unlocked.
3. Temporarily make X2D unreachable with a reversible action.
4. Confirm Diagnostics records a sanitized reconnect incident, normalized failure category and retry context.
5. Restore reachability.
6. Confirm automatic recovery without re-adding the printer.
7. Confirm credentials/access codes/raw vendor exceptions are absent from diagnostics.

**Pass:** reconnect is automatic, bounded and secret-safe after service restart and temporary network loss.

## No-print gate decision

Record PASS/FAIL for sections 1–6.

**GO to first print only if every no-print section passes on the exact same immutable candidate.**

If application code changes, stop, publish a new immutable candidate and repeat every affected observation. Never mix evidence across digests.

# First real print gate

## 7. Immutable 3MF review and explicit routing intent

Use a small known-safe X2D `.3mf` whose intended plate/materials are understood before the test.

Through the browser:

1. select the file;
2. compute/record SHA-256;
3. stage it into FoxForge content-addressed storage;
4. inspect the immutable 3MF print plan;
5. select the intended plate explicitly for multi-plate files;
6. review logical material requirements;
7. bind every required material to an explicit currently loaded physical source;
8. verify missing/stale/incompatible/ambiguous/unknown routes are blocked;
9. verify present-but-invalid toolhead metadata is blocked and cannot fall back to a fixed source route;
10. verify a blocked unselected plate does not poison a different safe selected plate;
11. enqueue without a client-owned `toolheadId`.

Record before Start:

- artifact SHA-256;
- selected plate;
- logical requirements;
- selected physical slot IDs/friendly labels;
- expected toolhead positions when present;
- any print-plan warning/blocker codes.

**Pass:** the job reaches the queue only with complete explicit operator intent and safe selected-plate routing evidence.

## 8. Exactly-once physical dispatch

1. press **Start** as a separate protected action;
2. verify server-side recompile/revalidation of current material-system/topology before submit;
3. verify FTPS/project storage upload completes;
4. verify Bambu `project_file` is accepted;
5. record dispatch ID and vendor job identity/acknowledgement when exposed;
6. capture effective `ams_mapping`, `ams_mapping2` and `nozzle_mapping` in a secret-safe form;
7. verify external 254/255 stays `-1` in flat `ams_mapping`, retains real source ID in `ams_mapping2`, and obtains a nozzle only from the compiler-owned toolhead;
8. verify exactly one intended physical print starts;
9. verify FoxForge observes that same active job/progress.

**Pass:** exactly one physical print starts from the reviewed intent. Any ambiguous outcome remains `INDETERMINATE`/reconciliation-bound and is not blindly retried.

## 9. Guarded job control

Against the same observed active job:

1. Pause and verify X2D pauses.
2. Resume and verify the same job resumes.
3. Cancel with explicit confirmation when appropriate, or allow completion.
4. Verify stale/incorrect job identity cannot control another job.
5. Verify an ambiguous control outcome is not automatically resent without reconciliation.

**Pass:** controls target only the exact observed job and ambiguous side effects are not automatically resent.

## 10. Evidence and Alpha 5 gate

Repository-safe evidence must include exact candidate identities, validation date, pass/fail per section, normalized errors/reconnect categories, material/topology observations, print-plan/binding facts, dispatch identity, physical start count and redacted screenshots/log excerpts where useful.

Before final `v0.1.0-alpha.5`:

| Gate | Required result |
| --- | --- |
| Replacement candidate identity | exact source/image/Umbrel package recorded |
| Umbrel install/update | exact package starts on Raspberry Pi 5 |
| Operator credential | visible via Umbrel UI and memory-only in browser |
| Add/Update | test-before-save, rollback and terminal replay proven |
| Discovery | bounded private suggestion/manual CIDR path proven |
| Reconnect/diagnostics | restart/network-loss recovery and redaction proven |
| Live Bambu state | real X2D state updates proven |
| AMS 2 Pro | A1–A4 PETG + Ext-L empty + Ext-R PLA observed |
| Material topology | Ext-L→left and Ext-R→right; stale/unknown fail closed |
| 3MF parser/routing | selected plate, explicit bindings, invalid-metadata blocker proven |
| Print dispatch | FTPS/project_file, effective mappings, exactly one physical start |
| Job control | guarded Pause/Resume/Cancel or completion path proven |
| Regression | exact-head backend/frontend/browser/container/security/ARM64/Umbrel gates green |

Only after the complete matrix passes:

1. update/close #115 with evidence references;
2. prepare final `v0.1.0-alpha.5` release identity/notes;
3. run exact-head release gates;
4. publish immutable Alpha 5 image and matching Store package;
5. reassess P3 and broader printer-family work after Alpha 5 stabilization.
