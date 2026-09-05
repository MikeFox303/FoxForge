# Alpha 4 Fix 2 physical-validation handoff — 2026-09-05

**Application release:** `v0.1.0-alpha.4.2`  
**Released application commit:** `fe5b3437f1e342548df74ded78557c771ef40710`  
**Validation-tooling baseline:** `1831992b87571a45753d8c97b8ae001514e8fce0`  
**Umbrel Store package commit:** `e842c411e26689609e9bbba4681df903f3624bbd`  
**State:** software publication is complete; representative physical/deployment validation is the remaining release-readiness gate.

This handoff deliberately separates the immutable application that was released from the newer repository-only validation tooling. Post-release testing changes do not alter the already published Alpha 4.2 image and must not be represented as application fixes included in that image.

## Frozen application identity

Canonical Alpha 4.2 application identity:

```text
release = v0.1.0-alpha.4.2
release commit = fe5b3437f1e342548df74ded78557c771ef40710
image = ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2
OCI index digest = sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6
exact image = ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6
platforms = linux/amd64, linux/arm64
```

The annotated tag resolves to release commit `fe5b3437f1e342548df74ded78557c771ef40710`. Release workflow `33973431720` completed successfully on that exact commit before the multi-architecture image and GitHub pre-release were published.

## Frozen Umbrel package identity

Canonical Store package:

```text
app id = my3d-foxforge
version = 0.1.0-alpha.4.2
Store commit = e842c411e26689609e9bbba4681df903f3624bbd
image = ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6
volume = ${APP_DATA_DIR}/data:/data
write bootstrap = FOXFORGE_COMMAND_TOKEN: "${APP_PASSWORD}"
```

The Store package is therefore the deployment target for representative Raspberry Pi 5/Umbrel validation. Do not substitute a floating tag, locally rebuilt image, current `main`, Alpha 4, or Alpha 4.1 package.

## Release freeze

Alpha 4.2 is frozen for physical validation. Open dependency/tooling upgrades are not part of this candidate and must not be merged into the Alpha 4.2 application identity after evidence collection has started.

At handoff time, open Dependabot work includes major/minor changes such as TypeScript 7, Vitest 4, i18next/react-i18next major upgrades, GitHub Actions major upgrades, Docker Actions major upgrades, and backend test-tool updates. Those changes belong to a later development/release cycle unless a security issue is severe enough to invalidate Alpha 4.2, in which case the correct response is to prepare a new release identity rather than silently changing Alpha 4.2.

P3 automatic filament accounting remains frozen in draft PR #58 until the physical/deployment resume gate is satisfied.

## Post-release validation-tooling hardening

The following changes were merged after the immutable Alpha 4.2 application release. They harden evidence collection/verification only; they do not change printer runtime, frontend behavior, deployment packaging, or the released container:

- PR #107, merge `1c644db5376967ef7ada8390dee8010dc6af32b0`: binds physical evidence verification to an explicitly expected release commit and package identity so evidence from another build fails closed.
- PR #108, merge `b484bbe34be9bedd2af7f8d40a06559a95157f1c`: physical HTTP probes refuse redirects so FoxForge bearer credentials and Moonraker API keys cannot be forwarded to a redirected endpoint.
- PR #109, merge `1831992b87571a45753d8c97b8ae001514e8fce0`: AUD-013/P3 now requires two distinct Bambu TLS evidence files and machine-checks MQTT and FTPS fingerprint stability across samples; one duplicated/single sample cannot satisfy the gate.

Canonical evidence verification should therefore use validation tooling from commit `1831992b87571a45753d8c97b8ae001514e8fce0` or a later commit that preserves these fail-closed rules, while the manifest `sourceCommit` remains the released application commit `fe5b3437f1e342548df74ded78557c771ef40710`.

## Required physical sequence

### 1. Raspberry Pi 5 / Umbrel

Install or update `my3d-foxforge` to `0.1.0-alpha.4.2` from the Store package above and verify the exact digest is installed. Back up `/data` before the update.

Required observations:

- clean start and health after installation/update;
- application restart and Umbrel/Raspberry Pi reboot with `/data` persistence;
- browser-facing App Proxy path works;
- protected UI writes require **Unlock writes** with the Umbrel app password;
- reloading the browser does not preserve the operator credential;
- direct backend reachability does not become an anonymous credential/bootstrap source;
- X2D and Moonraker/OpenKE are reachable from the deployment network namespace;
- representative SSE reconnect/resync works through the packaged deployment.

### 2. Bambu Lab X2D + AMS 2 Pro

Collect the first TLS fingerprint sample from the same network namespace used by FoxForge, perform a normal printer restart, then collect a second distinct sample.

Required observations:

- connect/reconnect and normalized state synchronization;
- AMS 2 Pro slot/material state is represented consistently;
- project storage/upload behavior;
- print-start acknowledgement;
- pause, resume and cancel;
- completion and ambiguous-outcome handling;
- MQTT and FTPS fingerprints are stable across the two actual restart-separated samples;
- correct MQTT/FTPS pins succeed;
- intentionally wrong MQTT pin fails closed;
- intentionally wrong FTPS pin fails closed;
- restoring correct pins recovers without deleting unrelated printer state.

A firmware-update fingerprint observation is preferred when practical, but must not be fabricated when no update is available.

### 3. Ender 3 V3 KE / OpenKE / Moonraker

Required observations:

- HTTP/WebSocket connect and reconnect;
- normalized live state;
- upload/checksum/start path;
- pause, resume and cancel;
- completion/failure;
- ambiguous command outcome handling.

## Evidence collection

Use the current runbook:

`docs/testing/physical-validation-runbook.md`

For Alpha 4.2 start from:

`docs/testing/evidence/alpha4.2-manifest.template.json`

The template intentionally starts every physical observation as `false` and references two distinct Bambu TLS sample files. Change an observation to `true` only after the corresponding behavior was actually observed.

Repository evidence must remain secret-safe:

- do not commit Bambu access codes;
- do not commit Umbrel app passwords or FoxForge command tokens;
- do not commit Moonraker API keys;
- keep IPs/URLs redacted in public evidence;
- record failures as well as successes.

Canonical verification identity:

```bash
SOURCE_COMMIT=fe5b3437f1e342548df74ded78557c771ef40710
PACKAGE_IDENTITY='ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6'

python -m foxforge.testing.physical_evidence \
  docs/testing/evidence/<validation>/manifest.json \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY" \
  --require p3
```

A valid manifest that is incomplete returns a non-zero gate result. A malformed, unsafe or identity-mismatched evidence package is rejected. The verifier cannot prove that the operator really restarted a physical printer, exercised a wrong certificate pin, or observed a printer lifecycle; those remain real-device observations.

## Go/no-go rules

Alpha 4.2 may remain the physical-validation target while all of the following are true:

- release tag still resolves to `fe5b3437f1e342548df74ded78557c771ef40710`;
- Store package remains pinned to OCI digest `sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6`;
- no newly discovered production/runtime/security defect invalidates the released image;
- physical evidence is collected against that exact package.

Prepare a new release version instead of reusing Alpha 4.2 if a production code, dependency, packaging, migration, security or printer-transport fix must be included before physical acceptance.

## Current gate

Software publication and package pinning are complete. `AUD-003` and `AUD-013` remain **`VALIDATION REQUIRED`**, and P3 remains frozen. The next meaningful release-readiness work is the representative Raspberry Pi 5/Umbrel + X2D/AMS 2 Pro + Ender 3 V3 KE/OpenKE physical run and secret-safe evidence review.
