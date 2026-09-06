# Physical validation evidence gate

- **Status:** implemented generic verifier contract
- **Updated:** 2026-09-06
- **Source audit:** `docs/audits/2026-09-04-independent-project-audit.md`
- **Active status:** `docs/audits/2026-09-04-remediation-tracker.md`

`python -m foxforge.testing.physical_evidence` verifies one operator evidence manifest plus referenced JSON probe outputs. It is deliberately release-agnostic: callers bind it to the exact candidate/release through expected identity arguments.

## What the verifier enforces

- closed manifest schema; unknown fields/observations are rejected;
- required observations are boolean and complete for the schema;
- `probeFiles` are unique, relative and contained inside the evidence directory;
- probe files use the supported schema, include successful probes and declare `secretValuesIncluded: false`;
- targets remain redacted unless a private validation explicitly allows them;
- source commit, package/image identity and validation date are present;
- supplied expected source/package identities must match exactly;
- AUD-013 requires at least two distinct successful Bambu TLS sample files with stable MQTT fingerprints and stable FTPS fingerprints;
- network probes alone cannot satisfy the complete P3 physical gate.

## Current target selection

The verifier does not define the current release target.

For the active Alpha 5 Bambu milestone, use:

- [Pre-Alpha 5 Bambu physical validation](pre-alpha-5-bambu-physical-validation.md);
- [`evidence/pre-alpha5-candidate4-manifest.template.json`](evidence/pre-alpha5-candidate4-manifest.template.json).

Candidate 1/2/3 templates and evidence remain historical and must not be relabeled for the Candidate 4 source/image identity. The older `alpha4.2-manifest.template.json` remains a historical Alpha 4.2 template and must not be used for new Pre-Alpha 5 evidence.

## Run the verifier

```bash
SOURCE_COMMIT='<exact source commit>'
PACKAGE_IDENTITY='<exact image@sha256:digest>'

python -m foxforge.testing.physical_evidence \
  docs/testing/evidence/<validation>/manifest.json \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY"
```

Optional gate requirements:

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

Exit status:

- `0` — manifest is valid, identity matched and selected gate complete;
- `1` — manifest is valid/identity-matched but selected gate incomplete;
- `2` — malformed, unsafe, structurally incomplete or identity-mismatched evidence.

## AUD-003

A deployment gate requires real representative evidence for the exact package, including install/restart/persistence, browser-facing protected write path, direct-backend fail-closed behavior, deployment-network printer reachability and representative realtime reconnect/resync.

Package CI or QEMU does not substitute for those observations.

## AUD-013

The Bambu certificate gate combines machine-checked and operator-observed evidence.

Machine checks require two distinct successful TLS sample files with stable MQTT and FTPS fingerprints across them. Operator evidence records the real restart and correct-pin/incorrect-pin/recovery behavior.

A manually set `fingerprintsStableAcrossRestart=true` cannot override missing or contradictory TLS samples.

## P3

The P3 gate additionally requires the complete physical lifecycle matrix declared by its current resume contract. It cannot become ready from reachability/certificate probes alone.

P3 remains frozen during the current Bambu Alpha 5 milestone.

## Evidence hygiene

Commit only redacted evidence. Never include printer access codes, API keys, app/operator credentials, session data or private authentication material.

A passing verifier means the evidence package is structurally complete for the selected gate and exact identity. It does not by itself authorize a release/audit status change without reviewing the real observations.
