# Physical and deployment validation runbook

**Related audit findings:** AUD-003, AUD-013  
**Purpose:** collect reproducible, secret-safe evidence from the real deployment/printer network before changing any `VALIDATION REQUIRED` finding to `RESOLVED`.

Automated CI proves code contracts, but it cannot prove that a physical Bambu X2D, Moonraker/OpenKE host or Raspberry Pi 5/Umbrel deployment behaves correctly on the operator's real network. This runbook defines the minimum evidence package.

AUD-004 is already resolved by the repository's representative reverse-proxy contract. The real Umbrel proxy path remains part of the broader deployment/P3 validation matrix and AUD-003 package evidence, but it does not reopen AUD-004.

## Validation probe

Current source provides:

```bash
python -m foxforge.testing.physical_validation --help
```

The probe uses only Python's standard library and does not print configured secret values.

By default target host/URL values are redacted from JSON evidence. Add `--include-targets` only when the resulting file is intentionally private and local addressing information is acceptable.

### Secret handling

Optional credentials are read from environment variables, never command-line values:

```bash
export FOXFORGE_VALIDATION_COMMAND_TOKEN='...'
export FOXFORGE_VALIDATION_MOONRAKER_API_KEY='...'
```

The generated JSON contains `"secretValuesIncluded": false` and must never contain the actual token/API key. Do not place Bambu LAN access codes in the probe command or evidence file.

## 1. Bambu X2D TLS certificate evidence — AUD-013

Run from the same host/network namespace that FoxForge will use to reach the printer, preferably the Raspberry Pi/Umbrel host for final evidence:

```bash
python -m foxforge.testing.physical_validation \
  --bambu-host <X2D_IP> \
  --output x2d-certificates-before.json
```

The probe performs TLS handshakes against the FoxForge default Bambu LAN services:

- MQTT: TCP 8883
- implicit FTPS: TCP 990

It records only the SHA-256 fingerprint of each presented certificate plus whether both services presented the same certificate.

Required AUD-013 sequence:

1. collect `before` fingerprints while the X2D is in the normal LAN-only/developer configuration used by FoxForge;
2. restart the printer normally and collect a second file;
3. verify whether MQTT and FTPS fingerprints remain stable across restart;
4. if practical, repeat after a firmware update before adopting a persistent default trust policy;
5. configure the observed fingerprints in a test FoxForge source deployment;
6. prove normal connect/state/project-storage behavior succeeds with the correct pins;
7. deliberately change the MQTT fingerprint and prove MQTT fails closed before subscription;
8. restore MQTT, deliberately change the FTPS fingerprint and prove FTPS fails closed before login/upload;
9. restore the correct values and prove recovery without deleting unrelated printer state.

Do **not** change the Bambu trust default solely because one certificate snapshot was obtainable. The decision depends on observed stability and update behavior.

## 2. Moonraker/OpenKE reachability

Run from the same deployment network namespace:

```bash
python -m foxforge.testing.physical_validation \
  --moonraker-url http://<ENDER_HOST>:7125 \
  --output moonraker-reachability.json
```

If the Moonraker instance requires an API key, export `FOXFORGE_VALIDATION_MOONRAKER_API_KEY` first. The probe requests `/server/info` and records only status/JSON-shape evidence.

This is a reachability/authentication prerequisite only. Full printer validation must still cover upload/checksum/start, live state, pause/resume/cancel, completion/failure and ambiguous command outcomes through FoxForge.

## 3. FoxForge deployment/auth boundary — AUD-003

Run through the **same browser-facing URL/proxy path** used by the operator. For a write-enabled deployment, export the FoxForge command token only in the shell environment:

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
- never submits a valid inventory object, so the auth-boundary check creates no spool.

For a future Umbrel package, run this through the actual Umbrel App Proxy/browser path and separately confirm the direct backend path does not become an anonymous credential source. This is AUD-003 package evidence; the generic proxy-security design itself is already covered by resolved AUD-004.

## 4. Combined host-network prerequisite probe

From Raspberry Pi 5/Umbrel, all three prerequisite checks can be collected together:

```bash
export FOXFORGE_VALIDATION_COMMAND_TOKEN='...'
export FOXFORGE_VALIDATION_MOONRAKER_API_KEY='...'   # only when required

python -m foxforge.testing.physical_validation \
  --bambu-host <X2D_IP> \
  --moonraker-url http://<ENDER_HOST>:7125 \
  --foxforge-url http://<FOXFORGE_URL> \
  --output foxforge-physical-prerequisites.json
```

Exit code is zero only when every requested probe passes.

## 5. Evidence manifest and verifier

The raw probe proves only prerequisite reachability/certificate/auth behavior. Operator-observed lifecycle evidence is captured in a strict manifest based on:

`docs/testing/evidence/physical-validation-manifest.example.json`

After the real-device run, verify it with:

```bash
python -m foxforge.testing.physical_evidence \
  docs/testing/evidence/<validation>/manifest.json
```

To require a specific gate:

```bash
python -m foxforge.testing.physical_evidence <manifest> --require aud003
python -m foxforge.testing.physical_evidence <manifest> --require aud013
python -m foxforge.testing.physical_evidence <manifest> --require p3
```

The verifier rejects missing observations, unknown fields, failed probes, evidence that is not marked secret-safe, and non-redacted targets by default. See `docs/testing/physical-evidence-gate.md` for the complete contract.

## Required full physical matrix before P3 resumes

The JSON probe is only the prerequisite/evidence collector. The following behavior still requires operator-observed real-device validation:

| Area | Minimum evidence |
| --- | --- |
| Raspberry Pi 5 / Umbrel | install, restart, persistence, browser/proxy path, migration/upgrade behavior, X2D/OpenKE reachability, SSE reconnect/resync |
| Bambu X2D | connect/reconnect, normalized state, project upload/storage, print-start acknowledgement, pause, resume, cancel, completion, ambiguous outcome handling |
| Moonraker/OpenKE | HTTP/WebSocket connect/reconnect, upload/checksum/start, pause, resume, cancel, completion/failure, ambiguous outcome handling |
| Browser auth | Add Printer and at least one other protected workflow through the exact packaged deployment; missing/invalid credential stays fail-closed |
| Bambu certificate trust | stable/repeatable MQTT + FTPS fingerprints, correct-pin success, independent wrong-pin fail-closed behavior, recovery, firmware-update observation where practical |

## Evidence file rules

When adding evidence under `docs/testing/evidence/` or linking it from the remediation tracker:

- do not commit access codes, API keys, command tokens, session tokens or cookies;
- target IPs/URLs should remain redacted in repository evidence;
- include FoxForge commit SHA, package/image identity and validation date in the evidence manifest;
- distinguish automated prerequisite output from operator-observed printer behavior;
- record failures as well as successes; do not discard evidence that changes the trust/deployment design conclusion;
- run `physical_evidence` successfully before proposing an audit-status change.

## Closure rules

- **AUD-003**: may move from `VALIDATION REQUIRED` to `RESOLVED` only after the exact future official package demonstrates truthful write-enabled or read-only behavior end to end and the corresponding evidence manifest passes `--require aud003`.
- **AUD-013**: requires physical X2D certificate stability/pinning evidence and a manifest passing `--require aud013` before any default TLS trust behavior is changed or the finding is resolved.
- **P3**: physical/deployment readiness additionally requires the complete Bambu + Moonraker/OpenKE lifecycle matrix and a manifest passing `--require p3`.

A successful network probe alone is not sufficient to close either remaining finding or to resume P3.
