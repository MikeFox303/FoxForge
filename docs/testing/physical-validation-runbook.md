# Physical and deployment validation runbook

- **Status:** generic, version-independent evidence procedure
- **Updated:** 2026-09-06
- **Related:** AUD-003, AUD-013, [physical evidence gate](physical-evidence-gate.md)

Automated CI proves software contracts; it cannot prove a physical printer, Raspberry Pi/Umbrel deployment or real LAN behaves correctly. This runbook defines reusable evidence rules without hardcoding one obsolete release identity.

> [!IMPORTANT]
> Always use the milestone-specific exact target. For the active Bambu milestone, use [Pre-Alpha 5 Bambu physical validation](pre-alpha-5-bambu-physical-validation.md). Historical Alpha 4.2 identities/templates remain historical only.

## Exact-target rule

Every evidence set records:

- exact FoxForge source commit used by the package;
- exact package version/role;
- exact image tag plus immutable OCI digest;
- Store/package commit when applicable;
- validation date;
- target hardware/deployment;
- referenced probe/evidence files.

Do not collect canonical evidence against `main`, a floating image tag, an unrecorded local rebuild or a different candidate and then relabel it.

## Validation probe

Current source provides:

```bash
python -m foxforge.testing.physical_validation --help
```

The probe is designed to avoid emitting configured secrets. HTTP probes refuse redirects so protected request credentials are not forwarded to a different target. Target addresses are redacted from repository-safe JSON by default.

Optional validation credentials should be supplied through environment variables documented by the probe rather than command-line literals.

## Bambu TLS certificate evidence

When AUD-013/certificate trust is part of the gate, collect at least two distinct successful Bambu TLS probe files around a real normal printer restart.

The probe records SHA-256 fingerprints for the Bambu MQTT and FTPS services without storing the printer access code. The verifier checks MQTT fingerprints across samples and FTPS fingerprints across samples. The operator separately records that the restart really occurred.

A complete trust observation also proves correct configured pins succeed, intentionally incorrect pins fail closed for the corresponding service, and restoring correct pins recovers without deleting unrelated printer state.

If samples disagree, record the result and keep the trust finding unresolved.

## Moonraker reachability

From the same deployment network namespace:

```bash
python -m foxforge.testing.physical_validation \
  --moonraker-url http://<PRINTER_HOST>:7125 \
  --output moonraker-reachability.json
```

This proves reachability/authentication shape only. Full hardware validation separately covers WebSocket state, upload/start, job control, completion/failure and ambiguous outcomes.

## FoxForge deployment/auth boundary

Through the same browser-facing path used by the operator:

```bash
python -m foxforge.testing.physical_validation \
  --foxforge-url http://<FOXFORGE_HOST>:<PORT> \
  --output foxforge-deployment-auth.json
```

Use the probe's documented environment variable when an application credential is required. Missing/incorrect authentication must remain fail-closed.

For Umbrel also prove manually that the app credential is obtainable through the intended UI flow, Operator Access works, the browser does not persist it across reload/tab lifecycle, and direct backend reachability does not create anonymous command authorization.

## Evidence manifest

Use [`evidence/physical-validation-manifest.example.json`](evidence/physical-validation-manifest.example.json) as the generic schema example or a milestone-specific template when one exists.

Validate against exact intended identities:

```bash
SOURCE_COMMIT='<exact source commit>'
PACKAGE_IDENTITY='<exact image tag@sha256:digest>'

python -m foxforge.testing.physical_evidence \
  docs/testing/evidence/<validation>/manifest.json \
  --expected-source-commit "$SOURCE_COMMIT" \
  --expected-package-identity "$PACKAGE_IDENTITY"
```

Use `--require aud003`, `--require aud013` or `--require p3` only when that gate is actually being evaluated.

## Full physical matrix

| Area | Representative observations |
| --- | --- |
| Deployment | install/update, restart, persistence, proxy/auth path, direct-backend fail-closed, SSE reconnect/resync |
| Bambu | add/update/reconnect, state/material sync, project storage, print start, job control, completion, ambiguous outcome handling |
| Moonraker | connect/reconnect, upload/checksum/start, job control, completion/failure, ambiguous outcome handling |
| Browser auth | correct credential works; missing/incorrect fails closed; memory-only lifecycle |
| Certificate trust | two stable TLS samples plus correct/incorrect pin and recovery behavior |

Milestone-specific runbooks may require a subset or additional observations.

## Evidence hygiene

Commit only secret-safe evidence. Record exact immutable build identities, keep machine probe results separate from operator-observed physical facts, retain failures rather than discarding them, and treat a changed source/image digest as a new target for affected observations.

## Closure rule

A green CI run, QEMU ARM64 smoke, package render or network probe is supporting evidence only. Validation-bound findings or release gates close only after the required real-device observations are reviewed and, where applicable, the repository evidence verifier passes for the exact target.
