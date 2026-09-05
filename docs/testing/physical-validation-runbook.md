# Physical and deployment validation runbook

**Related audit findings:** AUD-003, AUD-013  
**Purpose:** collect reproducible, secret-safe evidence from the real deployment/printer network before changing any `VALIDATION REQUIRED` finding to `RESOLVED`.

Automated CI proves code contracts, but it cannot prove that a physical Bambu X2D, Moonraker/OpenKE host or Raspberry Pi 5/Umbrel deployment behaves correctly on the operator's real network. This runbook defines the minimum evidence package.

AUD-004 is already resolved by the repository's representative reverse-proxy contract. The real Umbrel proxy path remains part of the broader deployment/P3 validation matrix and AUD-003 package evidence, but it does not reopen AUD-004.

## Physical-test target policy

Physical evidence must always identify the **exact published build actually installed**. Never record evidence against a branch, floating image tag or a planned release identity.

The current canonical physical-validation baseline is:

- Store app: `my3d-foxforge`
- package version: `0.1.0-alpha.4.2`
- FoxForge release: `v0.1.0-alpha.4.2`
- FoxForge release commit: `fe5b3437f1e342548df74ded78557c771ef40710`
- image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2`
- multi-architecture digest: `sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6`
- exact deployable image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6`
- published platforms: `linux/amd64`, `linux/arm64`
- Umbrel Store package merge: `e842c411e26689609e9bbba4681df903f3624bbd`
- application write credential: Umbrel `APP_PASSWORD` mapped by the package to `FOXFORGE_COMMAND_TOKEN`.

The release, immutable GHCR index and matching Store package now exist and agree, so canonical Alpha 4.2 physical evidence may begin. Evidence produced with Alpha 4 or Alpha 4.1 remains useful historical evidence but must not be relabeled as Alpha 4.2 evidence.

For Alpha 4.2, the evidence manifest must use release commit `fe5b3437f1e342548df74ded78557c771ef40710` as `sourceCommit` and the exact semantic-version-plus-digest image above as `packageIdentity`. Record Store commit `e842c411e26689609e9bbba4681df903f3624bbd` in the evidence directory README/run notes rather than appending it to `packageIdentity`, so the package identity remains machine-comparable.

The exact release commit passed backend lint/format/tests, frontend type/unit/build checks, the production-container browser acceptance matrix, deployment-authentication checks, dependency/image security gates, source-map absence and release-image smoke before the guarded release workflow created the tag and published the multi-architecture image. Browser evidence is retained separately from the OCI image identity.

Store CI proves package/Compose consistency plus anonymous `amd64`/`arm64` pull/start. The steps below collect the still-missing real hardware/deployment evidence.

## Validation probe

Current source provides:

```bash
python -m foxforge.testing.physical_validation --help
```

The probe uses only Python's standard library and does not print configured secret values. HTTP probes refuse redirects, so FoxForge Bearer credentials and Moonraker API keys remain bound to the operator-supplied target rather than being forwarded through a 3xx response.

By default target host/URL values are redacted from JSON evidence. Add `--include-targets` only when the resulting file is intentionally private and local addressing information is acceptable.

### Secret handling

Optional credentials are read from environment variables, never command-line values:

```bash
export FOXFORGE_VALIDATION_COMMAND_TOKEN='...'
export FOXFORGE_VALIDATION_MOONRAKER_API_KEY='...'
```

The generated JSON contains `"secretValuesIncluded": false` and must never contain the actual token/API key. Do not place Bambu LAN access codes in the probe command or evidence file.

For an Umbrel package, `FOXFORGE_VALIDATION_COMMAND_TOKEN` should contain the FoxForge app password shown by Umbrel. Do not commit or paste that real password into repository evidence.

## 1. Bambu X2D TLS certificate evidence — AUD-013

Run from the same host/network namespace that FoxForge will use to reach the printer, preferably the Raspberry Pi/Umbrel host for final evidence.

Before restart:

```bash
python -m foxforge.testing.physical_validation \
  --bambu-host <X2D_IP> \
  --output foxforge-physical-prerequisites.json
```

If collecting the combined prerequisite report, add the Moonraker/FoxForge arguments described below to this first command. The important requirement is that this file contains the first successful `bambu_tls` sample.

Then restart the X2D normally. After it is fully available again, collect a separate second TLS file:

```bash
python -m foxforge.testing.physical_validation \
  --bambu-host <X2D_IP> \
  --output x2d-certificates-after-restart.json
```

The probe performs TLS handshakes against the FoxForge default Bambu LAN services:

- MQTT: TCP 8883
- implicit FTPS: TCP 990

It records only the SHA-256 fingerprint of each presented certificate plus whether both services presented the same certificate.

The evidence verifier now requires at least two **distinct referenced probe files** containing successful Bambu TLS samples before AUD-013 can pass. It independently verifies that:

- every referenced MQTT fingerprint is identical across the samples;
- every referenced FTPS fingerprint is identical across the samples.

This machine check prevents `fingerprintsStableAcrossRestart=true` from overriding missing or contradictory certificate data. The boolean is still required because the verifier cannot prove that a real normal printer restart occurred between the two files; that part remains operator-observed evidence.

Required AUD-013 sequence:

1. collect the first fingerprints while the X2D is in the normal LAN-only/developer configuration used by FoxForge;
2. restart the printer normally and collect the second TLS file only after the printer is fully available again;
3. verify the evidence manifest reports `bambuTlsSampleFiles >= 2` and `bambuTlsStableAcrossSamples: true`;
4. only then mark `fingerprintsStableAcrossRestart=true` in the manifest;
5. if practical, repeat after a firmware update before adopting a persistent default trust policy;
6. configure the observed fingerprints in a test FoxForge deployment;
7. prove normal connect/state/project-storage behavior succeeds with the correct pins;
8. deliberately change the MQTT fingerprint and prove MQTT fails closed before subscription;
9. restore MQTT, deliberately change the FTPS fingerprint and prove FTPS fails closed before login/upload;
10. restore the correct values and prove recovery without deleting unrelated printer state.

If the two TLS samples disagree, record the mismatch and keep AUD-013 unresolved. Do **not** change the Bambu trust default solely because one certificate snapshot was obtainable or because an operator checkbox was set.

## 2. Moonraker/OpenKE reachability

Run from the same deployment network namespace:

```bash
python -m foxforge.testing.physical_validation \
  --moonraker-url http://<ENDER_HOST>:7125 \
  --output moonraker-reachability.json
```

If the Moonraker instance requires an API key, export `FOXFORGE_VALIDATION_MOONRAKER_API_KEY` first. The probe requests `/server/info` and records only status/JSON-shape evidence. Redirects are not followed.

This is a reachability/authentication prerequisite only. Full printer validation must still cover upload/checksum/start, live state, pause/resume/cancel, completion/failure and ambiguous command outcomes through FoxForge.

## 3. FoxForge deployment/auth boundary — AUD-003

Run through the **same browser-facing URL/proxy path** used by the operator. Export the app password only in the shell environment:

```bash
export FOXFORGE_VALIDATION_COMMAND_TOKEN='...'
python -m foxforge.testing.physical_validation \
  --foxforge-url http://<FOXFORGE_HOST>:<PORT> \
  --output foxforge-deployment-auth.json
```

The probe:

- verifies `/healthz`;
- performs a protected inventory POST using an intentionally invalid empty body;
- with a correct command token, expects authentication to pass and request validation to fail with HTTP 400 / `invalid_request` before any mutation;
- without a token, accepts only truthful fail-closed 401/503 behavior;
- never submits a valid inventory object, so the auth-boundary check creates no spool;
- refuses redirects rather than forwarding the command token to another HTTP target.

Run this through the actual Umbrel App Proxy/browser-facing path and separately confirm that the direct backend path does not become an anonymous credential source. This is AUD-003 package evidence; the generic proxy-security design itself is already covered by resolved AUD-004.

Also perform at least one real protected UI command after **Unlock writes** using the app password, then reload the page and confirm FoxForge asks for the credential again rather than persisting it in browser storage.

## 4. Combined host-network prerequisite probe

From Raspberry Pi 5/Umbrel, the first X2D sample plus Moonraker and FoxForge prerequisites can be collected together:

```bash
export FOXFORGE_VALIDATION_COMMAND_TOKEN='...'
export FOXFORGE_VALIDATION_MOONRAKER_API_KEY='...'   # only when required

python -m foxforge.testing.physical_validation \
  --bambu-host <X2D_IP> \
  --moonraker-url http://<ENDER_HOST>:7125 \
  --foxforge-url http://<FOXFORGE_URL> \
  --output foxforge-physical-prerequisites.json
```

Exit code is zero only when every requested probe passes. After the normal X2D restart, collect the second Bambu-only file separately as shown in section 1. A duplicate reference to the same JSON file is rejected by the evidence verifier and cannot satisfy the two-sample AUD-013 requirement.

## 5. Evidence manifest and verifier

The raw probe proves only prerequisite reachability/certificate/auth behavior. Operator-observed lifecycle evidence is captured in a strict manifest.

For the current Alpha 4.2 run, start from:

`docs/testing/evidence/alpha4.2-manifest.template.json`

The generic schema example remains available at:

`docs/testing/evidence/physical-validation-manifest.example.json`

The Alpha 4.2 template already contains the correct non-secret identities, references the expected prerequisite and post-restart TLS files, and keeps all operator observations `false`. Copy it into a new evidence directory and change values only when the corresponding real behavior has been observed.

Canonical Alpha 4.2 manifest identity:

```text
sourceCommit = fe5b3437f1e342548df74ded78557c771ef40710
packageIdentity = ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6
Store commit (run notes) = e842c411e26689609e9bbba4681df903f3624bbd
```

After the real-device run, bind verification to those exact release identities:

```bash
SOURCE_COMMIT=fe5b3437f1e342548df74ded78557c771ef40710
PACKAGE_IDENTITY='ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6'

python -m foxforge.testing.physical_evidence \
  docs/testing/evidence/<validation>/manifest.json \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY"
```

For a valid two-sample X2D evidence set, inspect the emitted fields:

```text
bambuTlsSampleFiles >= 2
bambuTlsStableAcrossSamples = true
```

To require a specific gate, keep the same expected identity arguments:

```bash
python -m foxforge.testing.physical_evidence <manifest> \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY" \
  --require aud003

python -m foxforge.testing.physical_evidence <manifest> \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY" \
  --require aud013

python -m foxforge.testing.physical_evidence <manifest> \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY" \
  --require p3
```

An identity mismatch is rejected with verifier exit code `2`; it cannot produce a passing AUD-003, AUD-013 or P3 result for the intended release. Missing or mismatched before/after TLS data keeps AUD-013/P3 incomplete even when operator booleans are true. The expected-identity flags remain generic, so historical/future evidence can be checked against their own exact identities.

The verifier also rejects duplicate probe paths, missing observations, unknown fields, failed probes, evidence that is not marked secret-safe, and non-redacted targets by default. See `docs/testing/physical-evidence-gate.md` for the complete contract.

## Required full physical matrix before P3 resumes

The JSON probe is only the prerequisite/evidence collector. The following behavior still requires operator-observed real-device validation:

| Area | Minimum evidence |
| --- | --- |
| Raspberry Pi 5 / Umbrel | install/update of the exact Alpha 4.2 package, restart, persistence, browser/proxy write path, direct-backend fail-closed behavior, migration/upgrade behavior, X2D/OpenKE reachability, SSE reconnect/resync |
| Bambu X2D | connect/reconnect, normalized state, project upload/storage, print-start acknowledgement, pause, resume, cancel, completion, ambiguous outcome handling |
| Moonraker/OpenKE | HTTP/WebSocket connect/reconnect, upload/checksum/start, pause, resume, cancel, completion/failure, ambiguous outcome handling |
| Browser auth | Add Printer and at least one other protected workflow through the exact packaged deployment; missing/invalid credential stays fail-closed; reload clears memory-only credential |
| Bambu certificate trust | two distinct before/after-restart TLS evidence files with stable MQTT + FTPS fingerprints, correct-pin success, independent wrong-pin fail-closed behavior, recovery, firmware-update observation where practical |

## Evidence file rules

When adding evidence under `docs/testing/evidence/` or linking it from the remediation tracker:

- do not commit access codes, API keys, command tokens, app passwords, session tokens or cookies;
- target IPs/URLs should remain redacted in repository evidence;
- include FoxForge release commit SHA, exact package/image/digest identity, Store package commit and validation date in the evidence manifest/run notes;
- use distinct files for before/after-restart Bambu TLS observations; duplicate `probeFiles` entries are rejected;
- distinguish machine-checked fingerprint equality from the operator-observed fact that a real restart occurred between samples;
- distinguish automated prerequisite output from operator-observed printer behavior;
- record failures as well as successes; do not discard evidence that changes the trust/deployment design conclusion;
- run `physical_evidence` with the exact expected release/package identity before proposing an audit-status change.

## Closure rules

- **AUD-003**: may move from `VALIDATION REQUIRED` to `RESOLVED` only after the exact published `my3d-foxforge` package demonstrates the configured write-enabled behavior end to end on representative Raspberry Pi/Umbrel and the corresponding evidence manifest passes `--require aud003` with the expected Alpha 4.2 identities.
- **AUD-013**: requires two distinct successful before/after-restart X2D TLS probe files with machine-verified stable MQTT and FTPS fingerprints, plus the physical correct-pin/wrong-pin/recovery observations, before a manifest may pass `--require aud013` with the expected Alpha 4.2 identities.
- **P3**: physical/deployment readiness additionally requires the complete Bambu + Moonraker/OpenKE lifecycle matrix and a manifest passing `--require p3` with the exact intended release/package identity.

A successful Store CI run or network probe alone is not sufficient to close either remaining finding or to resume P3.
