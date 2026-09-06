# Pre-Alpha 5 Bambu physical validation

- **Target milestone:** `v0.1.0-alpha.5`
- **Tracking:** [#115](https://github.com/MikeFox303/FoxForge/issues/115)
- **Status:** validation candidate 4 published; no-print physical gate required before the first real print
- **Updated:** 2026-09-06

This is the current milestone-specific source of truth for the Bambu/X2D Alpha 5 release gate. Generic evidence rules remain in [physical-validation-runbook.md](physical-validation-runbook.md) and [physical-evidence-gate.md](physical-evidence-gate.md).

## Exact validation candidate

All new Pre-Alpha 5 evidence must identify this exact application build:

```text
FoxForge source commit: c11f7145b4354aa79c8f0fad223648240e652bac
image tag: ghcr.io/mikefox303/foxforge:sha-c11f714
OCI digest: sha256:75d656bafcafb4e0e566548f6cca941244d29fef1bbc5be98e425f375246056a
exact image: ghcr.io/mikefox303/foxforge:sha-c11f714@sha256:75d656bafcafb4e0e566548f6cca941244d29fef1bbc5be98e425f375246056a
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.4
Umbrel Store commit: 07b8e8087ac9897d4c2f5dc45944b48dfb0938e1
base semantic release: v0.1.0-alpha.4.3
target semantic release: v0.1.0-alpha.5
```

The Store package is intentionally a validation candidate, not final Alpha 5. Candidate 1, 2 and 3 evidence remains historical and must not be relabeled as Candidate 4 evidence. Documentation-only commits may advance FoxForge `main` after `c11f7145...`; they do not change the immutable application source or image under test.

## Target environment

Primary acceptance target:

- Raspberry Pi 5 + UmbrelOS;
- `my3d-foxforge` installed from the Community Store;
- Bambu Lab X2D reachable from the FoxForge container network namespace;
- AMS 2 Pro connected to the X2D;
- browser access through the normal Umbrel App Proxy path.

Representative material fixture for the current X2D acceptance run:

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

Record Candidate 4 application source, immutable image digest and Store commit separately from any later documentation-only FoxForge commit used to record the evidence.

# No-print physical gate

Sections 1–6 must pass on Candidate 4 **without starting a physical print**. Do not proceed to section 7 until the complete no-print gate is green.

## 1. Install and identity

1. Refresh the Community Store.
2. Confirm package `0.1.0-alpha.4.3-umbrel.4` is offered.
3. Install/update without editing Compose or container settings manually.
4. Confirm `/healthz` succeeds through the normal app path.
5. Record the exact source/image/digest/Store identities above in private run notes.
6. Confirm the installed package still uses Umbrel App Proxy and ordinary bridge networking; do not switch to host networking as a test workaround.

**Pass:** the exact Candidate 4 package starts normally on Raspberry Pi 5/Umbrel and its identity matches the pinned image above.

## 2. GUI-only Operator Access

1. Obtain the FoxForge app credential from the Umbrel UI.
2. Open FoxForge through Umbrel.
3. Use **Operator Access / Unlock writes**.
4. Execute a protected low-risk setup action.
5. Reload the page and verify the browser no longer holds write access.
6. Verify missing/incorrect credentials fail closed.

**Pass:** no terminal lookup is required and the browser credential remains memory-only.

## 3. Bambu discovery and Add Printer

Exercise Candidate 4 subnet suggestions when they are available from the server-visible deployment network, and keep manual CIDR entry as the fallback.

1. Open Add Printer → Bambu Lab.
2. Confirm suggested networks, if present, are bounded private RFC1918 networks rather than arbitrary/public ranges.
3. Select a sensible suggested subnet or enter the actual private CIDR manually.
4. Run discovery and verify results remain candidates only.
5. Verify X2D metadata is sensible and normal live Test connection succeeds with valid configuration.
6. Add the printer and confirm persistence occurs only after successful preflight.

Negative cases:

- unreachable/wrong host;
- wrong LAN access code;
- wrong serial number.

**Pass:** discovery never bypasses authenticated setup preflight, failed Add leaves no dead configured printer, and errors are normalized/actionable without raw internal exceptions.

## 4. Safe Update rollback and terminal replay

Starting from the known-good configured X2D:

1. change one connectivity/identity field to an intentionally invalid value;
2. submit Update;
3. verify preflight rejects the replacement;
4. confirm the original configuration remains present and reconnectable;
5. restore/use valid settings and confirm normal operation;
6. through the applicable regression path, confirm replaying the same terminal failed setup command identity does not execute a second setup attempt.

**Pass:** invalid replacement data cannot destroy a working printer configuration and terminal failed setup replay is deterministic.

## 5. Live X2D, AMS 2 Pro and material topology

Verify real updates for connection/operational state and the typed material read models.

Required physical observations for the current fixture:

- AMS 2 Pro is identified as a four-slot unit;
- A1, A2, A3 and A4 report PETG;
- External Left is present as a physical source and reports empty;
- External Right is present as a physical source and reports PLA;
- topology reports External Left → Left toolhead;
- topology reports External Right → Right toolhead;
- route/toolhead presentation comes from `foxforge.material_topology`, not a generic UI model-name guess;
- stale or unknown topology is visibly non-authoritative rather than shown as a proven route;
- FoxForge spool inventory identity remains separate from physical printer material state.

If the real printer reports additional route metadata, record it without converting unknown/dynamic values into a fixed route unless FoxForge itself proves that route.

**Pass:** the material-system and topology UI match the actual X2D/AMS/external setup above and no left/right route is invented from ambiguous evidence.

## 6. Restart, network loss and diagnostics

1. Restart the FoxForge app/container and confirm the saved X2D reconnects automatically.
2. Restart/reload through the normal Umbrel path and confirm Operator Access remains locked until explicitly unlocked again.
3. Temporarily make the X2D unreachable with a reversible action.
4. Confirm Diagnostics records a sanitized reconnect incident, normalized failure category and retry context.
5. Restore reachability.
6. Confirm automatic recovery without re-adding the printer.
7. Confirm credentials, access codes, private auth material and raw vendor exceptions do not appear in diagnostics.

**Pass:** reconnect is automatic, bounded and secret-safe after both service restart and temporary network loss.

## No-print gate decision

Before any physical Start action, record PASS/FAIL for sections 1–6.

**GO to first print only if every no-print section passes on the exact Candidate 4 identity.**

If any section fails because of application code, stop, fix the defect, publish a new immutable candidate and repeat every affected observation. Do not continue to a print using mixed evidence from different source/image digests.

# First real print gate

## 7. Immutable 3MF review and explicit routing intent

Use a small, known-safe X2D `.3mf` whose intended plate/materials are understood before the test.

Through the browser:

1. select the file;
2. compute/record its SHA-256;
3. stage it into FoxForge content-addressed artifact storage;
4. inspect the immutable 3MF print plan;
5. select the intended plate explicitly when the file has multiple plates;
6. review each logical material requirement;
7. bind every required logical material to an explicit currently loaded physical source;
8. verify the UI shows the expected material family and proven route/toolhead, and blocks missing, stale, incompatible, ambiguous or unknown routing;
9. enqueue the reviewed job without a client-owned `toolheadId`.

Record before Start:

- artifact SHA-256;
- selected plate;
- logical material requirements;
- selected physical slot IDs/friendly labels;
- expected toolhead positions reported by the 3MF when present.

**Pass:** the job reaches the queue only with complete explicit operator material intent; FoxForge does not auto-pick a spool/source or guess a nozzle.

## 8. Exactly-once physical dispatch

Use the queued job from section 7.

1. press **Start** as a separate protected action;
2. verify the server recompiles/revalidates the current material system/topology before submit;
3. verify project storage/FTPS upload completes;
4. verify the Bambu `project_file` submission is accepted;
5. record the dispatch ID and vendor job identity/acknowledgement when exposed;
6. capture the effective `ams_mapping`, `ams_mapping2` and `nozzle_mapping` evidence in a secret-safe form;
7. verify external source 254/255 encoding, when used, stays `-1` in flat `ams_mapping`, uses the real source in `ams_mapping2`, and obtains a nozzle only from the proven compiled toolhead;
8. verify the physical X2D starts exactly one intended job;
9. verify FoxForge observes that same active job/progress.

**Pass:** exactly one physical print starts from the explicit reviewed intent. Any ambiguous outcome remains `INDETERMINATE`/reconciliation-bound and is not blindly retried.

## 9. Guarded job control

Against the same observed active job:

1. Pause and verify the X2D pauses.
2. Resume and verify the same job resumes.
3. Test Cancel with explicit confirmation when appropriate, or allow completion.
4. Verify stale/incorrect job identity cannot control an unrelated job.
5. Verify an ambiguous control outcome is not automatically resent without reconciliation.

**Pass:** common job controls target only the exact observed job and ambiguous side effects are not automatically resent.

## 10. Evidence

Repository-safe evidence should include exact candidate identities, validation date, pass/fail per section, normalized error/reconnect categories, material/topology observations, print-plan/binding facts, dispatch identity, physical start count and redacted screenshots/log excerpts where useful.

A starter verifier-compatible manifest is [`evidence/pre-alpha5-candidate4-manifest.template.json`](evidence/pre-alpha5-candidate4-manifest.template.json).

Keep richer operator notes/screenshots beside the manifest rather than adding undeclared fields to the verifier's closed schema.

## Alpha 5 release gate

| Gate | Required result |
| --- | --- |
| Umbrel install/update | exact Candidate 4 starts on Raspberry Pi 5 |
| Operator credential | visible via Umbrel UI and memory-only in FoxForge browser |
| Add Printer | valid X2D succeeds; wrong host/code/serial are non-persistent |
| Update Printer | invalid replacement preserves the previous working configuration |
| Failed setup replay | same logical terminal failure is not re-executed |
| Discovery | bounded private suggestions/manual CIDR remain candidate-only and cannot bypass authenticated preflight |
| Reconnect | restart/network-loss recovery proven with sanitized diagnostics |
| Live Bambu state | real X2D state updates proven |
| AMS 2 Pro | A1–A4 PETG plus external Left empty / external Right PLA observed |
| Material topology | external Left→left and external Right→right proven; unknown/stale remains fail-closed |
| 3MF review | selected plate, requirements and explicit physical bindings recorded before Start |
| Print dispatch | real FTPS/project_file start proven with effective mappings and no duplicate start |
| Job control | real guarded Pause/Resume/Cancel or completion path proven |
| Regression | backend/frontend/browser/container/Umbrel package gates remain green |

If physical testing requires implementation changes, publish a new immutable candidate and repeat every affected observation. Do not carry Candidate 1/2/3 evidence across the Candidate 4 source/image digest without explicit revalidation.

## After the gate

Only after the complete matrix passes:

1. update/close #115 with Candidate 4 evidence references;
2. prepare final `v0.1.0-alpha.5` release notes and release identity;
3. run exact-head backend/frontend/browser/container/security/ARM64/Umbrel release gates;
4. publish the immutable Alpha 5 semantic image and matching Store package;
5. reassess P3 and broader printer-family work after Alpha 5 stabilization.
