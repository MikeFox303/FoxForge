# Pre-Alpha 5 Bambu physical validation

- **Target milestone:** `v0.1.0-alpha.5`
- **Tracking:** [#115](https://github.com/MikeFox303/FoxForge/issues/115)
- **Status:** validation candidate 3 published; real-device evidence required before final Alpha 5
- **Updated:** 2026-09-06

This is the current milestone-specific source of truth for the Bambu/X2D Alpha 5 release gate. Generic evidence rules remain in [physical-validation-runbook.md](physical-validation-runbook.md) and [physical-evidence-gate.md](physical-evidence-gate.md).

## Exact validation candidate

All current Pre-Alpha 5 evidence must identify this exact build:

```text
FoxForge source commit: 37d1cbed8f73d62acdc1994545bc2f5ee57e816a
image tag: ghcr.io/mikefox303/foxforge:sha-37d1cbe
OCI digest: sha256:4e652006212db2527804abbd478b7b64fde127414b1dbe22703854280ccfce82
exact image: ghcr.io/mikefox303/foxforge:sha-37d1cbe@sha256:4e652006212db2527804abbd478b7b64fde127414b1dbe22703854280ccfce82
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.3
Umbrel Store commit: cc6010fdff4823b671a92be3b307155f26db85bc
base semantic release: v0.1.0-alpha.4.3
target semantic release: v0.1.0-alpha.5
```

The package is intentionally a validation candidate, not final Alpha 5. Candidate 1 and candidate 2 evidence remain historical and must not be relabeled as candidate 3 evidence. Candidate 3 is required because the material-routing, queue integration and Bambu nozzle-mapping implementation changed after candidate 2.

## Target environment

Primary acceptance target:

- Raspberry Pi 5 + UmbrelOS;
- `my3d-foxforge` installed from the Community Store;
- Bambu Lab X2D reachable from the FoxForge container network namespace;
- AMS 2 Pro connected to the X2D;
- browser access through the normal Umbrel App Proxy path.

Physical material fixture for the current X2D acceptance:

```text
X2D
├─ AMS 2 Pro
│  ├─ A1 PETG
│  ├─ A2 PETG
│  ├─ A3 PETG
│  └─ A4 PETG
├─ External Left
│  └─ empty
└─ External Right
   └─ PLA
```

Where the printer exposes authoritative routing metadata, FoxForge must represent External Left as the left-toolhead source and External Right as the right-toolhead source. Unknown or dynamic routing must remain unknown/dynamic rather than being guessed.

Moonraker/OpenKE remains a separate physical track. P3 automatic filament accounting stays frozen during this Bambu milestone.

## Evidence hygiene

Do not commit operator credentials, printer access codes, API keys, cookies, session data or unredacted private network targets. Use normalized FoxForge error categories and redacted evidence only.

For print-routing evidence, record normalized logical material indices, source slot IDs, toolhead IDs and sanitized command mapping fields. Do not capture credentials or raw transport payloads that contain sensitive values.

## Acceptance sequence

### 1. Install and identity

1. Refresh the Community Store.
2. Confirm package `0.1.0-alpha.4.3-umbrel.3` is offered.
3. Install/update without editing Compose or container settings manually.
4. Confirm `/healthz` succeeds through the normal app path.
5. Record the exact source/image/digest/Store identities above in private run notes.

**Pass:** the exact candidate starts normally on Raspberry Pi 5/Umbrel.

### 2. GUI-only Operator Access

1. Obtain the FoxForge app credential from the Umbrel UI.
2. Open FoxForge through Umbrel.
3. Use **Operator Access / Unlock writes**.
4. Execute a protected low-risk setup action.
5. Reload the page and verify the browser no longer holds write access.
6. Verify missing/incorrect credentials fail closed.

**Pass:** no terminal lookup is required and the browser credential remains memory-only.

### 3. Bambu discovery and Add Printer

Exercise discovery when practical and manual entry as fallback.

Verify that discovery is candidate-only, the X2D metadata is sensible, normal live Test connection succeeds with valid configuration, and Add persists only after successful preflight.

Negative cases:

- unreachable/wrong host;
- wrong LAN access code;
- wrong serial number.

**Pass:** failed Add leaves no dead configured printer and shows a normalized actionable error without raw internal exceptions.

### 4. Safe Update rollback

Starting from the known-good configured X2D:

1. change one connectivity/identity field to an intentionally invalid value;
2. submit Update;
3. verify preflight rejects the replacement;
4. confirm the original configuration remains present and reconnectable;
5. restore/use valid settings and confirm normal operation;
6. through the applicable regression path, confirm replaying the same terminal failed setup command identity does not execute a second setup attempt.

**Pass:** invalid replacement data cannot destroy a working printer configuration and terminal failed setup replay is deterministic.

### 5. Live X2D and AMS 2 Pro state

Verify real updates for connection/operational state, current job/progress when applicable, currently mapped telemetry, AMS 2 Pro units/slots/material state, active source when reported and both external feed/source positions when reported.

For the current fixture verify at minimum:

- the AMS is identified as AMS 2 Pro when native metadata proves that subtype;
- A1-A4 are present and report PETG;
- External Left is represented and empty;
- External Right is represented and reports PLA;
- source-to-toolhead routing is represented only when proved by current native metadata;
- the UI does not collapse the two external sources into one generic external tray.

**Pass:** values originate from real printer state, topology is truthful, and FoxForge inventory identity remains separate from physical AMS state.

### 6. Restart and reconnect

1. Restart the FoxForge app/container.
2. Confirm the saved X2D reconnects automatically.
3. Temporarily make the X2D unreachable with a reversible action.
4. Confirm Diagnostics records a sanitized reconnect incident and retry context.
5. Restore reachability.
6. Confirm automatic recovery without re-adding the printer.
7. Confirm credentials and raw vendor exceptions do not appear in diagnostics.

**Pass:** reconnect is automatic, bounded and secret-safe.

### 7. Real print dispatch and material routing

Use a small known-safe X2D `.3mf` whose intended plate/material/nozzle use is known before the run.

1. Select/hash/stage it through the browser and record the staged artifact SHA-256.
2. Inspect the immutable staged `.3mf` print plan before enqueue.
3. Record the selected plate and normalized material requirements, including material index and target toolhead/nozzle when present in the artifact.
4. Select the connected X2D.
5. Explicitly bind every required logical material to a currently loaded physical material source. Do not rely on automatic material/color substitution.
6. Review the compiler-owned source-to-toolhead result. Ambiguous, missing, stale or unsupported routing must block before adapter assessment/submit.
7. Enqueue the artifact only after the routing assessment is eligible.
8. Press **Start** as a separate protected action.
9. Immediately before Bambu transport submission, verify the selected source remains present and the native topology still proves the compiled toolhead route.
10. Verify project storage/upload completes.
11. Record sanitized command mapping evidence for the exact dispatch:
    - logical material index;
    - selected physical source slot;
    - compiled toolhead;
    - flat `ams_mapping` entry;
    - `ams_mapping2` entry when applicable;
    - `nozzle_mapping` entry.
12. For Bambu external source IDs 254/255, verify flat `ams_mapping` uses `-1`, the real external source ID is retained in `ams_mapping2`, and nozzle selection comes only from the compiled toolhead route.
13. Verify the print submission is accepted.
14. Verify the physical X2D starts exactly one intended job.
15. Verify FoxForge observes the same active vendor job/progress.

**Pass:** every required material has a proven physical source/toolhead path, the serialized Bambu mappings match that proven route, and exactly one print starts. Any ambiguous outcome remains `INDETERMINATE`/reconciliation-bound and is not blindly retried.

### 8. Guarded job control

Against the same observed active job:

1. Pause and verify the X2D pauses.
2. Resume and verify the same job resumes.
3. Test Cancel with explicit confirmation when appropriate, or allow completion.
4. Verify stale/incorrect job identity cannot control an unrelated job.

**Pass:** common job controls target only the exact observed job and ambiguous side effects are not automatically resent.

### 9. Evidence

Repository-safe evidence should include exact candidate identities, validation date, pass/fail per section, normalized error/reconnect categories, the sanitized routing/mapping facts above, redacted screenshots/log excerpts where useful and follow-up issue references for failures.

A starter manifest is [`evidence/pre-alpha5-candidate3-manifest.template.json`](evidence/pre-alpha5-candidate3-manifest.template.json).

## Alpha 5 release gate

| Gate | Required result |
| --- | --- |
| Umbrel install/update | exact candidate starts on Raspberry Pi 5 |
| Operator credential | visible via Umbrel UI and memory-only in FoxForge browser |
| Add Printer | valid X2D succeeds; wrong host/code/serial are non-persistent |
| Update Printer | invalid replacement preserves the previous working configuration |
| Failed setup replay | same logical terminal failure is not re-executed |
| Discovery | candidate-only and cannot bypass authenticated preflight |
| Reconnect | restart/network-loss recovery proven with sanitized diagnostics |
| Live Bambu state | real X2D state updates proven |
| AMS 2 Pro | A1-A4 PETG plus both external sources observed truthfully |
| Material topology | external left/right and source-to-toolhead routing are proved or explicitly unknown; never guessed |
| 3MF print plan | selected plate/material requirements/toolheads are inspected from the immutable staged artifact |
| Material binding | every required material is explicitly bound to a current physical source |
| Bambu command mapping | `ams_mapping` / `ams_mapping2` / `nozzle_mapping` match the compiled route |
| Print dispatch | real project upload/start proven without duplicate start |
| Job control | real guarded Pause/Resume/Cancel or completion path proven |
| Regression | backend/frontend/browser/container/Umbrel package gates remain green |

If physical testing requires implementation changes, publish a new immutable candidate and repeat every affected observation. Do not carry candidate 1 or candidate 2 evidence across candidate 3 without explicit revalidation.

## After the gate

Only after the complete matrix passes:

1. update/close #115 with evidence references;
2. prepare final `v0.1.0-alpha.5` release notes and release identity;
3. run exact-head backend/frontend/browser/container/security/ARM64/Umbrel release gates;
4. publish the immutable Alpha 5 semantic image and matching Store package;
5. reassess P3 and broader printer-family work after Alpha 5 stabilization.
