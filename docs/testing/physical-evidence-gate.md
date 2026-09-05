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
- successful network probes alone are never enough to satisfy the full P3 physical gate.

The example manifest is `docs/testing/evidence/physical-validation-manifest.example.json`.

## Workflow

1. Build/install the exact candidate that is being validated. For current Umbrel validation this is `my3d-foxforge` `0.1.0-alpha.4`, pinned to multi-architecture digest `sha256:0b0d96e5243db82ad3349bbc1c96243cbc6288c27eb716ff80512eb925b9fef4`.
2. From the real FoxForge deployment network namespace, collect the prerequisite probes described in `physical-validation-runbook.md`.
3. Copy the example manifest next to the redacted probe JSON files.
4. Replace `sourceCommit`, `packageIdentity`, `validationDate` and `probeFiles` with the exact evidence identities.
5. Change an observation to `true` only after that behavior has actually been observed on the real device/deployment.
6. Run the verifier before committing evidence.

```bash
python -m foxforge.testing.physical_evidence \
  docs/testing/evidence/<validation>/manifest.json
```

To require a particular audit gate:

```bash
python -m foxforge.testing.physical_evidence <manifest> --require aud003
python -m foxforge.testing.physical_evidence <manifest> --require aud013
python -m foxforge.testing.physical_evidence <manifest> --require p3
```

Exit status is:

- `0` when the manifest is valid and the selected gate is complete;
- `1` when the manifest is valid but the selected gate is incomplete;
- `2` when evidence is malformed, unsafe or structurally incomplete.

## AUD-003 evidence

`AUD-003 ready` requires:

- a successful FoxForge deployment/auth probe;
- installation of the exact candidate package;
- persistence across restart;
- protected browser writes through the actual browser-facing proxy path;
- proof that direct backend reachability does not become an anonymous operator-session source;
- X2D and Moonraker reachability from the deployment namespace;
- representative SSE reconnect/resync through that deployment.

This remains package-specific. Source-only Docker success, Store CI, QEMU `arm64` success and Compose validation do not automatically validate the published `alpha.4` Umbrel package on a real Raspberry Pi/Umbrel deployment. The current package software/bootstrap contract is already merged; AUD-003 now requires the real observations above rather than a hypothetical future package.

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

## Evidence hygiene

Commit only redacted evidence. Do not place access codes, API keys, command/session tokens, cookies or private certificates in the manifest or probe files. If local targets must be retained for a private troubleshooting record, keep that copy outside the public repository; the repository verifier defaults to rejecting visible targets.

A passing verifier means the submitted evidence package is complete for the declared observations. It does **not** authorize changing a finding to `RESOLVED` without reviewing the evidence and updating the remediation tracker through the normal PR process.
