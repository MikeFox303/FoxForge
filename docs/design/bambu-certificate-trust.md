# Bambu certificate trust

- **Status:** optional pinning implemented; real X2D trust evidence still required
- **Updated:** 2026-09-06
- **Related:** AUD-013, [physical evidence gate](../testing/physical-evidence-gate.md)

## Problem

Bambu LAN MQTT and FTPS are TLS services, but a self-hosted application cannot assume the printer presents a certificate chaining to ordinary public roots. Disabling certificate validation entirely would permit an active LAN attacker to impersonate the printer and receive credentials/commands.

FoxForge therefore separates transport compatibility from explicit identity pinning.

## Current policy

Bambu settings may independently configure:

- `mqtt_certificate_sha256`;
- `ftps_certificate_sha256`.

Pins are canonical SHA-256 fingerprints. Invalid values fail during configuration parsing. When a pin is present, the presented peer certificate must match before the corresponding authenticated MQTT/FTPS operation continues.

A mismatch becomes a normalized, non-retryable authentication failure. Public errors must not echo the expected or observed fingerprint.

MQTT and FTPS pins are independent because they may present different certificates.

## Default trust

The alpha default remains compatibility-oriented when no pin is configured, but this is **not** a claim that unpinned transport identity is proven safe for every Bambu firmware/device.

FoxForge will not switch to mandatory pinning or invent a first-use persistence scheme solely from CI. Real representative X2D evidence must establish certificate behavior across normal restart and the correct/incorrect-pin recovery path.

## Evidence requirement

AUD-013 requires real evidence for the exact target package:

1. at least two successful MQTT/FTPS TLS samples around a real normal X2D restart;
2. stable MQTT fingerprint across samples;
3. stable FTPS fingerprint across samples;
4. configured correct MQTT/FTPS pins succeed;
5. intentionally incorrect MQTT pin fails closed;
6. intentionally incorrect FTPS pin fails closed;
7. restoring correct pins recovers without deleting unrelated printer state.

The repository verifier validates sample consistency but cannot prove that the operator actually restarted the physical printer; that remains an observed fact recorded in the evidence manifest/run notes.

## Secret handling

Fingerprints are not printer credentials, but public diagnostics/errors still avoid exposing trust details unnecessarily. Bambu access codes remain separate SecretStore data and must never be included in TLS evidence.

## Future policy

After representative physical evidence, FoxForge may choose one of these explicitly documented paths:

- keep optional pinning as a hardening feature;
- ship a documented known trust anchor if the vendor provides a stable verifiable chain;
- add a carefully designed operator-approved first-use/rotation workflow.

Any change to default trust semantics requires release notes, tests and an updated ADR/design rationale.
