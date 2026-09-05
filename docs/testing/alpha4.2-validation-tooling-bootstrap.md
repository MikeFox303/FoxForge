# Alpha 4.2 validation-tooling bootstrap

**Purpose:** run the post-release physical evidence collector/verifier without modifying the frozen FoxForge `v0.1.0-alpha.4.2` application image.

The application being validated and the tooling used to collect/verify evidence are intentionally separate identities.

## Exact identities

Frozen application under test:

```text
release = v0.1.0-alpha.4.2
release commit = fe5b3437f1e342548df74ded78557c771ef40710
image = ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6
Umbrel Store package commit = e842c411e26689609e9bbba4681df903f3624bbd
```

Minimum validation-tooling baseline:

```text
1831992b87571a45753d8c97b8ae001514e8fce0
```

That tooling baseline includes the post-release fail-closed improvements from PRs #107–#109: expected release/package identity checks, no-follow HTTP redirects for credentialed probes, and two-sample Bambu MQTT/FTPS TLS stability verification.

Using newer validation tooling is acceptable only when it preserves or strengthens these rules. It does not change the manifest `sourceCommit`: Alpha 4.2 evidence must still identify the released application commit `fe5b3437f1e342548df74ded78557c771ef40710`.

## Do not install the tooling into the Alpha 4.2 app

Do not rebuild the released image, replace files inside the running FoxForge container, install a newer FoxForge package over it, or point the Umbrel package at `main` merely to obtain the evidence tools.

Use a separate temporary checkout. The collector and verifier use Python standard-library functionality and can be run directly from `backend/src` by setting `PYTHONPATH`; a package installation is not required for these modules.

## Bootstrap a separate checkout

On the machine from which evidence will be collected:

```bash
VALIDATION_TOOLING_COMMIT=1831992b87571a45753d8c97b8ae001514e8fce0

git clone https://github.com/MikeFox303/FoxForge.git foxforge-validation
cd foxforge-validation
git checkout --detach "$VALIDATION_TOOLING_COMMIT"

export PYTHONPATH="$PWD/backend/src"
python3 -m foxforge.testing.physical_validation --help
python3 -m foxforge.testing.physical_evidence --help
```

If a later repository commit is intentionally used for validation tooling, record that tooling commit in the private run notes/evidence-directory README. Do not change the application release identity in the evidence manifest.

If `git` is not available on the representative host, prepare the exact checkout on another trusted machine and transfer that source tree without secrets. Do not copy app `/data`, Bambu access codes, Umbrel passwords, Moonraker API keys, browser cookies or other credentials into the tooling checkout.

## Network-context rule

The tooling checkout location and the network location are separate concerns.

Network-sensitive prerequisite probes must be executed from a host/network context representative of the deployed FoxForge instance. For final AUD-003/AUD-013 evidence, prefer the Raspberry Pi/Umbrel deployment host or another context that has the same effective reachability to X2D and OpenKE/Moonraker.

A successful probe from a Windows workstation does not prove that the Raspberry Pi/Umbrel deployment can reach the same printer. Conversely, failure from an unrelated workstation does not prove that the packaged deployment is broken.

Record the actual execution context in private run notes, while public repository evidence keeps target IPs/URLs redacted.

## Create an evidence workspace

From the validation checkout:

```bash
RUN_ID="alpha4.2-$(date +%Y%m%d)"
EVIDENCE_DIR="docs/testing/evidence/$RUN_ID"
mkdir -p "$EVIDENCE_DIR"
cp docs/testing/evidence/alpha4.2-manifest.template.json "$EVIDENCE_DIR/manifest.json"
```

Before committing anything, set `validationDate` in the copied manifest and keep all physical observations `false` until the behavior has actually been observed.

The Alpha 4.2 template expects two distinct Bambu TLS-bearing files:

```text
foxforge-physical-prerequisites.json
x2d-certificates-after-restart.json
```

Do not duplicate one file under two names to satisfy the two-sample requirement.

## Secret-safe credential setup

Optional HTTP credentials are supplied only through environment variables:

```bash
export FOXFORGE_VALIDATION_COMMAND_TOKEN='...'
export FOXFORGE_VALIDATION_MOONRAKER_API_KEY='...'   # only when required
```

Do not put these values on the command line or in evidence JSON. The collector must emit `"secretValuesIncluded": false`.

For the packaged Umbrel deployment, `FOXFORGE_VALIDATION_COMMAND_TOKEN` is the app password that Umbrel supplies to FoxForge as `FOXFORGE_COMMAND_TOKEN`. Do not commit that password.

## Collect the first prerequisite/TLS sample

From the representative deployment network context:

```bash
python3 -m foxforge.testing.physical_validation \
  --bambu-host <X2D_IP> \
  --moonraker-url http://<ENDER_HOST>:7125 \
  --foxforge-url http://<FOXFORGE_BROWSER_FACING_HOST>:<PORT> \
  --output "$EVIDENCE_DIR/foxforge-physical-prerequisites.json"
```

Omit the Moonraker API-key environment variable when it is not required. Do not use `--include-targets` for evidence intended for the public repository.

This combined report supplies the first Bambu TLS sample plus FoxForge and Moonraker prerequisite probes.

## Collect the second X2D TLS sample

Perform a **real normal X2D restart**. Wait until the printer is fully available again, then run:

```bash
python3 -m foxforge.testing.physical_validation \
  --bambu-host <X2D_IP> \
  --output "$EVIDENCE_DIR/x2d-certificates-after-restart.json"
```

The verifier can compare the two MQTT/FTPS fingerprints, but it cannot prove that a physical restart happened between samples. Mark `fingerprintsStableAcrossRestart=true` only after the restart was actually performed and the two samples correspond to before/after observations.

## Verify the frozen Alpha 4.2 identity

Use the immutable application identities, not the validation-tooling commit:

```bash
SOURCE_COMMIT=fe5b3437f1e342548df74ded78557c771ef40710
PACKAGE_IDENTITY='ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6'

python3 -m foxforge.testing.physical_evidence \
  "$EVIDENCE_DIR/manifest.json" \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY"
```

For the TLS prerequisite to be machine-valid, verifier output must show at least:

```text
bambuTlsSampleFiles >= 2
bambuTlsStableAcrossSamples = true
```

That result does not by itself close AUD-013; the correct-pin, independent wrong-MQTT-pin, wrong-FTPS-pin, recovery and real restart observations are still required.

## Gate checks

After the corresponding real observations have been recorded in the manifest, evaluate the gates separately:

```bash
python3 -m foxforge.testing.physical_evidence \
  "$EVIDENCE_DIR/manifest.json" \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY" \
  --require aud003

python3 -m foxforge.testing.physical_evidence \
  "$EVIDENCE_DIR/manifest.json" \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY" \
  --require aud013

python3 -m foxforge.testing.physical_evidence \
  "$EVIDENCE_DIR/manifest.json" \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY" \
  --require p3
```

Exit code `0` means the selected gate is complete for the submitted manifest. Exit code `1` means the evidence package is valid but that gate is incomplete. Exit code `2` means the evidence is malformed, unsafe or identity-mismatched.

## Public evidence hygiene

Before opening an evidence PR:

- verify every target is `redacted`;
- verify `secretValuesIncluded` is `false` in every probe file;
- search the evidence directory for access codes, app passwords, bearer tokens, API keys, cookies and local URLs/IPs;
- record the validation-tooling commit in run notes, but keep `sourceCommit` set to the released Alpha 4.2 application commit;
- record Store package commit `e842c411e26689609e9bbba4681df903f3624bbd` in run notes;
- retain failures and contradictory observations rather than editing them away;
- do not change `AUD-003`/`AUD-013` to `RESOLVED` merely because a probe returned success.

See `docs/testing/physical-validation-runbook.md` for the complete behavioral matrix and `docs/status/alpha4-fix2-physical-validation-handoff-2026-09-05.md` for the Alpha 4.2 release-freeze rules.
