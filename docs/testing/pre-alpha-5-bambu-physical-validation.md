# Pre-Alpha 5 Bambu physical validation

- **Target milestone:** `v0.1.0-alpha.5`
- **Tracking:** [#115](https://github.com/MikeFox303/FoxForge/issues/115)
- **Status:** validation candidate 2 published; real-device evidence required before final Alpha 5
- **Updated:** 2026-09-06

This is the current milestone-specific source of truth for the Bambu/X2D Alpha 5 release gate. Generic evidence rules remain in [physical-validation-runbook.md](physical-validation-runbook.md) and [physical-evidence-gate.md](physical-evidence-gate.md).

## Exact validation candidate

All current Pre-Alpha 5 evidence must identify this exact build:

```text
FoxForge source commit: 37b253f385c19451c7ea075a4a4d12378cf17cf2
image tag: ghcr.io/mikefox303/foxforge:sha-37b253f
OCI digest: sha256:e550c8026ed6ec80e973d91fe6d96cc1474d537ca87de7875ec54f4a03aaaa4f
exact image: ghcr.io/mikefox303/foxforge:sha-37b253f@sha256:e550c8026ed6ec80e973d91fe6d96cc1474d537ca87de7875ec54f4a03aaaa4f
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.2
Umbrel Store commit: 1d7d78d7a0f3c36805071dd6d8078033c59672ac
base semantic release: v0.1.0-alpha.4.3
target semantic release: v0.1.0-alpha.5
```

The package is intentionally a validation candidate, not final Alpha 5. Candidate 1 evidence remains historical and must not be relabeled as candidate 2 evidence.

## Target environment

Primary acceptance target:

- Raspberry Pi 5 + UmbrelOS;
- `my3d-foxforge` installed from the Community Store;
- Bambu Lab X2D reachable from the FoxForge container network namespace;
- AMS 2 Pro connected to the X2D;
- browser access through the normal Umbrel App Proxy path.

Moonraker/OpenKE remains a separate physical track. P3 automatic filament accounting stays frozen during this Bambu milestone.

## Evidence hygiene

Do not commit operator credentials, printer access codes, API keys, cookies, session data or unredacted private network targets. Use normalized FoxForge error categories and redacted evidence only.

## Acceptance sequence

### 1. Install and identity

1. Refresh the Community Store.
2. Confirm package `0.1.0-alpha.4.3-umbrel.2` is offered.
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

Verify real updates for connection/operational state, current job/progress when applicable, currently mapped telemetry, AMS 2 Pro units/slots/material state, active source when reported and external feed/source when present.

**Pass:** values originate from real printer state, and FoxForge inventory identity remains separate from physical AMS state.

### 6. Restart and reconnect

1. Restart the FoxForge app/container.
2. Confirm the saved X2D reconnects automatically.
3. Temporarily make the X2D unreachable with a reversible action.
4. Confirm Diagnostics records a sanitized reconnect incident and retry context.
5. Restore reachability.
6. Confirm automatic recovery without re-adding the printer.
7. Confirm credentials and raw vendor exceptions do not appear in diagnostics.

**Pass:** reconnect is automatic, bounded and secret-safe.

### 7. Real print dispatch

Use a small known-safe X2D `.3mf`.

1. Select/hash/stage it through the browser.
2. Enqueue it for the connected X2D.
3. Start/dispatch as a separate protected action.
4. Verify project storage/upload completes.
5. Verify the print submission is accepted.
6. Verify the physical X2D starts exactly one intended job.
7. Verify FoxForge observes the same active job/progress.

**Pass:** exactly one print starts. Any ambiguous outcome remains `INDETERMINATE`/reconciliation-bound and is not blindly retried.

### 8. Guarded job control

Against the same observed active job:

1. Pause and verify the X2D pauses.
2. Resume and verify the same job resumes.
3. Test Cancel with explicit confirmation when appropriate, or allow completion.
4. Verify stale/incorrect job identity cannot control an unrelated job.

**Pass:** common job controls target only the exact observed job and ambiguous side effects are not automatically resent.

### 9. Evidence

Repository-safe evidence should include exact candidate identities, validation date, pass/fail per section, normalized error/reconnect categories, redacted screenshots/log excerpts where useful and follow-up issue references for failures.

A starter manifest is [`evidence/pre-alpha5-candidate2-manifest.template.json`](evidence/pre-alpha5-candidate2-manifest.template.json).

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
| AMS 2 Pro | physical slot/material/source observation proven |
| Print dispatch | real project upload/start proven without duplicate start |
| Job control | real guarded Pause/Resume/Cancel or completion path proven |
| Regression | backend/frontend/browser/container/Umbrel package gates remain green |

If physical testing requires implementation changes, publish a new immutable candidate and repeat every affected observation. Do not carry candidate 2 evidence across a changed source/image digest without explicit revalidation.

## After the gate

Only after the complete matrix passes:

1. update/close #115 with evidence references;
2. prepare final `v0.1.0-alpha.5` release notes and release identity;
3. run exact-head backend/frontend/browser/container/security/ARM64/Umbrel release gates;
4. publish the immutable Alpha 5 semantic image and matching Store package;
5. reassess P3 and broader printer-family work after Alpha 5 stabilization.
