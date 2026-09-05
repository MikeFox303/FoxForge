# Physical validation evidence gate

**Purpose:** turn the remaining real-device/deployment validation into a reproducible repository gate without pretending that CI can replace physical observations.

The source audit remains `docs/audits/2026-09-04-independent-project-audit.md`. The active status lives in `docs/audits/2026-09-04-remediation-tracker.md`.

## What this gate does

`python -m foxforge.testing.physical_evidence` verifies one operator evidence manifest plus the referenced JSON outputs created by `python -m foxforge.testing.physical_validation`.

The verifier is intentionally strict:

- the manifest schema is closed; unknown top-level fields and unknown observation names are rejected;
- every required observation must be present and boolean;
- probe files must use schema version 1, contain at least one successful probe and declare `secretValuesIncluded: false`;
- probe targets must remain `redacted` unless the verifier is explicitly run with `--allow-targets`;
- the evidence is tied to an exact source commit, package/image identity and validation date;
- callers can require an expected release commit and package identity; a mismatch is rejected before a gate can pass;
- successful network probes alone are never enough to satisfy the full P3 physical gate.

The generic example manifest is `docs/testing/evidence/physical-validation-manifest.example.json`. For the current release, prefer `docs/testing/evidence/alpha4.2-manifest.template.json`, which is prefilled with the exact non-secret Alpha 4.2 release identities but deliberately contains no successful physical observations.

## Current exact validation target

Canonical Alpha 4 Fix 2 physical evidence must use the package that is now published in the companion Umbrel Store:

- Store app: `my3d-foxforge`;
- package version: `0.1.0-alpha.4.2`;
- FoxForge release: `v0.1.0-alpha.4.2`;
- release commit: `fe5b3437f1e342548df74ded78557c771ef40710`;
- Store package commit: `e842c411e26689609e9bbba4681df903f3624bbd`;
- image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6`;
- platforms: `linux/amd64`, `linux/arm64`.

Do not collect new canonical Alpha 4.2 evidence against a floating tag, `main`, an older Alpha 4/4.1 package, or a locally rebuilt image. Historical evidence for older packages remains historical and must not be relabeled.

For repository evidence, keep `packageIdentity` machine-comparable: use the exact versioned image plus OCI digest shown above. Record Store commit `e842c411e26689609e9bbba4681df903f3624bbd` in the evidence directory README/run notes or remediation record rather than appending it to `packageIdentity`.

## Workflow

1. Install/update the exact `my3d-foxforge` `0.1.0-alpha.4.2` package identified above and verify the installed image still resolves to the recorded immutable digest.
2. From the real FoxForge deployment network namespace, collect the prerequisite probes described in `physical-validation-runbook.md`.
3. Copy `docs/testing/evidence/alpha4.2-manifest.template.json` next to the redacted probe JSON files.
4. Keep the prefilled Alpha 4.2 `sourceCommit` and `packageIdentity` unchanged; replace `validationDate` and `probeFiles` as needed for the actual run.
5. Change an observation to `true` only after that behavior has actually been observed on the real device/deployment.
6. Run the verifier with the expected Alpha 4.2 identities before committing evidence.

```bash
SOURCE_COMMIT=fe5b3437f1e342548df74ded78557c771ef40710
PACKAGE_IDENTITY='ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6'

python -m foxforge.testing.physical_evidence \
  docs/testing/evidence/<validation>/manifest.json \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY"
```

To require a particular audit gate, keep the same expected-identity arguments:

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

The expected-identity flags are generic and can be used for future or historical releases by supplying those releases' exact identities. They are not hard-coded to Alpha 4.2 in the verifier.

Exit status is:

- `0` when the manifest is valid, matches any supplied expected identities, and the selected gate is complete;
- `1` when the manifest is valid and identity-matched but the selected gate is incomplete;
- `2` when evidence is malformed, unsafe, structurally incomplete, or does not match a supplied expected release/package identity.

## AUD-003 evidence

`AUD-003 ready` requires:

- a successful FoxForge deployment/auth probe;
- installation of the exact candidate package;
- persistence across restart;
- protected browser writes through the actual browser-facing proxy path;
- proof that direct backend reachability does not become an anonymous operator-session source;
- X2D and Moonraker reachability from the deployment namespace;
- representative SSE reconnect/resync through that deployment.

This remains package-specific. Source-only Docker success, Store CI, QEMU `arm64` success and Compose validation do not automatically validate the published Alpha 4.2 Umbrel package on a real Raspberry Pi/Umbrel deployment. The current package software/bootstrap contract is already merged; AUD-003 now requires the real observations above rather than a hypothetical future package.

## AUD-013 evidence

`AUD-013 ready` requires a successful real Bambu TLS probe plus operator evidence that:

- MQTT and FTPS fingerprints are stable across a normal X2D restart;
- the observed correct pins allow their corresponding services to work;
- an intentionally wrong MQTT pin fails closed;
- an intentionally wrong FTPS pin fails closed;
- restoring the correct pins recovers without deleting unrelated printer state.

A firmware-update observation is strongly preferred before changing the default trust model, but the verifier does not fabricate such an observation when no update is available during the validation window.

## P3 physical gate

`P3 physical gate ready` additionally requires the complete real-device lifecycle matrix for Bambu and Moonraker/OpenKE. It therefore cannot become true from certificate/reachability probes alone.

The gate covers the minimum behaviors already required by the P3 frozen-state document: connect/reconnect, state synchronization, upload/start, common controls, completion/failure and ambiguous-outcome handling.

For the canonical Alpha 4.2 resume decision, a `p3PhysicalGateReady=true` result is acceptable only when the verifier was also invoked with the exact Alpha 4.2 `--expected-source-commit` and `--expected-package-identity` values above.

## Evidence hygiene

Commit only redacted evidence. Do not place access codes, API keys, command/session tokens, cookies or private certificates in the manifest or probe files. If local targets must be retained for a private troubleshooting record, keep that copy outside the public repository; the repository verifier defaults to rejecting visible targets.

A passing verifier means the submitted evidence package is complete for the declared observations and, when expected-identity arguments were supplied, belongs to the intended release package. It does **not** authorize changing a finding to `RESOLVED` without reviewing the evidence and updating the remediation tracker through the normal PR process.
