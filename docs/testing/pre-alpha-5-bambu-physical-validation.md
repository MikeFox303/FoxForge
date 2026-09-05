# Pre-Alpha 5 Bambu physical validation

**Milestone:** `v0.1.0-alpha.5`  
**Tracking:** #115  
**Status:** installable validation candidate published; real-device evidence required before final Alpha 5 release.

This runbook narrows the existing generic physical-validation process to the Pre-Alpha 5 Bambu milestone. It does not replace `docs/testing/physical-validation-runbook.md` or the physical-evidence verifier; it defines the exact candidate and Bambu/X2D acceptance sequence for #115.

## Exact validation candidate

Evidence must be collected against this exact published package/build:

- FoxForge source commit: `e7d4d77612890157203239f8d97a6c4abc328859`
- image tag: `ghcr.io/mikefox303/foxforge:sha-e7d4d77`
- immutable multi-architecture digest: `sha256:877ab4a53a6c8106482fa25d88f1f4ab52d26ba04f5be271e7f5efdd557258d1`
- exact image: `ghcr.io/mikefox303/foxforge:sha-e7d4d77@sha256:877ab4a53a6c8106482fa25d88f1f4ab52d26ba04f5be271e7f5efdd557258d1`
- Umbrel package version: `0.1.0-alpha.4.3-umbrel.1`
- Umbrel Store merge: `622c618e496d5aae1512414e621e5809bcf016d9`
- intended final release after successful evidence: `v0.1.0-alpha.5`

The Umbrel package is deliberately a validation candidate, not a semantic Alpha 5 release. Its package contract records the published Alpha 4.3 base, Alpha 5 target, exact source commit and immutable digest. Do not relabel evidence from another image/package as Pre-Alpha 5 evidence.

## Target hardware and deployment

Primary acceptance target:

- Raspberry Pi 5 running UmbrelOS;
- FoxForge installed through `my3d-foxforge` from the Community Store;
- Bambu Lab X2D reachable on the same real LAN path used by the container;
- AMS 2 Pro connected to the X2D;
- browser access through the normal Umbrel App Proxy path.

Moonraker/OpenKE remains a separate validation track. P3 automatic filament accounting stays frozen during this Bambu milestone.

## Secret handling

Never commit or paste into repository evidence:

- Umbrel app password / `APP_PASSWORD`;
- `FOXFORGE_COMMAND_TOKEN`;
- Bambu LAN access code;
- API keys, cookies or session tokens;
- unredacted local addresses unless the evidence is intentionally kept private.

The Umbrel app password is the FoxForge operator token for this package. Obtain it from the Umbrel UI, enter it only into FoxForge **Unlock writes**, and confirm it is not retained after a page reload/tab restart.

## Acceptance sequence

### 1. Install and identity

1. Refresh the Community App Store and confirm FoxForge package `0.1.0-alpha.4.3-umbrel.1` is offered.
2. Install/update FoxForge.
3. Confirm `/healthz` is healthy through the normal app path.
4. Record the Store commit, source commit and immutable digest above in the private run notes.

**Pass:** the exact candidate starts on Raspberry Pi 5/Umbrel without manual container edits or host-network privileges.

### 2. Operator unlock without terminal lookup

1. Obtain the FoxForge app password from the Umbrel UI.
2. Open FoxForge through Umbrel.
3. Use **Unlock writes** with that password.
4. Run one protected no-risk workflow, such as opening Add Printer and reaching the authenticated setup path.
5. Reload the page and confirm writes are locked again.

**Pass:** no terminal command is needed to discover the credential; missing/wrong credentials fail closed; reload clears the memory-only browser credential.

### 3. Add real X2D

Use **Add Printer → Bambu Lab (LAN mode)**.

Validate both discovery and manual fallback when practical:

- select/enter X2D host;
- enter normalized printer serial;
- enter LAN access code;
- select/confirm X2D model;
- run the connection test and add operation.

Negative cases must also be observed using intentionally wrong values without exposing them in evidence:

- unreachable/wrong host;
- wrong LAN access code;
- wrong serial number.

**Pass:** correct data connects and persists; failed setup does not leave a dead configured printer; UI shows normalized actionable error categories and never exposes raw Python exceptions such as `NoneType ... await`.

### 4. Live state and AMS 2 Pro

After connection, verify live updates for the physical printer:

- connection/operational state;
- current job/progress when applicable;
- temperatures and other currently mapped live telemetry;
- AMS 2 Pro physical slot/material state;
- external spool state when present;
- stale/offline state distinguished from physically empty/no-material state.

**Pass:** values change from real printer events rather than static placeholders; AMS data is physical printer state and is not silently conflated with FoxForge inventory identity.

### 5. Restart and reconnect supervisor

1. Restart the FoxForge app/container from Umbrel.
2. Confirm the saved X2D reconnects automatically without being re-added.
3. Make the X2D temporarily unreachable using a reversible network/printer action.
4. Confirm Diagnostics shows a sanitized reconnect incident with retry/backoff state.
5. Restore reachability.
6. Confirm automatic recovery and updated last-success/recovery state.

**Pass:** no reconnect storm; no manual config rewrite; one unavailable printer does not block FoxForge startup; raw vendor/transport secrets are not exposed.

### 6. Real print dispatch

Use a small known-safe `.3mf` suitable for the X2D.

1. Stage/upload it through the FoxForge browser workflow.
2. Enqueue it for the connected X2D.
3. Press **Start** separately.
4. Verify the FTPS upload/project-storage step completes.
5. Verify MQTT `project_file` submission is accepted and the physical X2D starts the intended job.
6. Confirm FoxForge observes the same job/progress live.

**Pass:** exactly one intended print starts. If the remote result is ambiguous, FoxForge preserves `INDETERMINATE` semantics and does not blindly retry the side effect.

### 7. Guarded job control

During the same known active print:

1. Pause from FoxForge and verify the X2D pauses.
2. Resume and verify the same job resumes.
3. Either allow the job to finish or test Cancel after explicit confirmation.
4. Verify stale/incorrect job identity is rejected rather than applied to an unrelated job.

**Pass:** Pause/Resume/Cancel operate only against the observed active job and ambiguous transport outcomes are not automatically retried unsafely.

### 8. Evidence and failure recording

Record both successful and failed observations. Repository-safe evidence should include only:

- exact candidate identities listed above;
- validation date;
- pass/fail result per acceptance section;
- normalized FoxForge error/reconnect categories;
- redacted screenshots/log excerpts where useful;
- any required follow-up issue references.

Do not change #115 to complete and do not create final `v0.1.0-alpha.5` while any required physical step remains unverified.

## Alpha 5 release gate

Final Alpha 5 is allowed only when all of the following are true:

| Gate | Required result |
| --- | --- |
| Umbrel install/update | exact candidate starts on Raspberry Pi 5 |
| Operator token | obtainable via Umbrel UI; protected writes fail closed otherwise |
| X2D setup | real successful add; wrong host/code/serial are actionable and non-persistent |
| Restart/reconnect | automatic reconnect and network-loss recovery proven |
| Live Bambu state | real X2D state updates proven |
| AMS 2 Pro | physical slot/material state proven |
| Print dispatch | real `.3mf` upload + MQTT start proven without duplicate dispatch |
| Job control | real Pause/Resume/Cancel or completion path proven with job guard |
| Diagnostics | secret-safe reconnect/setup diagnosis proven |
| Regression | backend/frontend/browser/container/Umbrel package CI remains green |

If a physical observation contradicts the current transport/security design, fix the implementation first, publish a new immutable validation candidate, and repeat the affected evidence. Do not carry old evidence forward to a new image digest without explicitly revalidating the changed path.

## After this gate

Once the complete X2D/AMS evidence is recorded:

1. close or update #115 with exact evidence references;
2. prepare final `v0.1.0-alpha.5` release notes/changelog;
3. run the full backend/frontend/browser/container/ARM64/Umbrel release gates;
4. publish the immutable Alpha 5 OCI image and matching Umbrel package;
5. only after Alpha 5 stabilization decide whether to resume P3 automatic filament accounting and broader Moonraker/vendor expansion.
