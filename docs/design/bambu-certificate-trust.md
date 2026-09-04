# Bambu LAN certificate trust

Status: software foundation implemented for AUD-013; physical X2D validation required before changing defaults.

## Context

Bambu LAN MQTT and implicit FTPS use TLS, but local printer certificates are commonly not rooted in a public CA. FoxForge therefore historically defaulted to `tls_verify=false`. The access code authenticates the client to the printer, but it does not prove that the TLS peer is the expected physical printer.

Changing the default to normal public-CA validation without device evidence could make supported LAN printers unreachable. Conversely, permanent certificate verification bypass should not be the final trust model.

## Decision

FoxForge adds optional SHA-256 certificate pinning at the Bambu wire boundary while preserving the current compatibility default until hardware validation is complete.

MQTT and FTPS have **independent pins**:

```text
mqtt_tls_certificate_sha256
ftps_tls_certificate_sha256
```

This deliberately avoids assuming that the printer's MQTT and FTPS services always present the same certificate across models or firmware versions.

A configured pin is checked after the TLS handshake and before FoxForge accepts the service for use:

- MQTT: before report-topic subscription and before `connect()` is considered successful;
- FTPS: after implicit TLS connection but before username/access-code login or file transfer.

A mismatch fails closed as a normalized Bambu transport rejection with vendor code `certificate_mismatch`. Error text does not disclose the configured or observed fingerprint.

## Interaction with `tls_verify`

Certificate pinning and normal CA/hostname verification are independent controls:

- `tls_verify=false`, no pin: current compatibility behavior;
- `tls_verify=false`, pin set: self-signed/device-local certificate is allowed to handshake but must match the configured SHA-256 pin;
- `tls_verify=true`, no pin: normal Python CA/hostname verification;
- `tls_verify=true`, pin set: both normal verification and the explicit pin must succeed.

The remediation does **not** change the default value of `tls_verify`.

## Pin representation

Pins are SHA-256 digests of the peer's DER certificate. FoxForge accepts 64 hexadecimal characters with or without colon separators and normalizes them to lowercase hex internally.

Fingerprint values are device trust metadata rather than authentication credentials. They may remain in normal private runtime configuration, but public read DTOs do not need to expose them.

## TOFU direction

A future Trust On First Use flow may build on this primitive, but automatic first-use enrollment is intentionally deferred. A safe TOFU design must define:

1. how the first fingerprint is obtained and shown to the operator;
2. whether MQTT and FTPS are enrolled independently;
3. how certificate rotation is distinguished from an unexpected peer change;
4. how a replacement printer with the same configured identity is approved;
5. where the trust record is persisted and audited;
6. what the UI does when a stored pin changes.

FoxForge must not silently replace an existing trust record after a mismatch.

## Physical validation gate

Before changing Bambu defaults or enabling automatic TOFU, validate on a real X2D installation:

1. capture the MQTT peer SHA-256 certificate fingerprint through a controlled diagnostic path;
2. capture the implicit-FTPS control-channel fingerprint independently;
3. determine whether the two certificates are identical on the tested firmware, without making that an architectural assumption;
4. reconnect repeatedly and confirm fingerprints remain stable;
5. restart the printer and repeat;
6. validate status/subscription with the MQTT pin enabled;
7. validate a harmless FTPS upload with the FTPS pin enabled;
8. intentionally configure a wrong pin and prove FoxForge fails closed before MQTT subscription / FTPS login;
9. record printer model and firmware alongside the evidence.

The current source must continue to report AUD-013 as validation-required until this evidence exists.

## Acceptance criteria

- [x] certificate pinning remains inside `foxforge.adapters.bambu` and does not leak into common printer contracts;
- [x] MQTT and FTPS pins are independent;
- [x] SHA-256 pin syntax is validated and normalized;
- [x] MQTT pin is checked before subscription/connection success;
- [x] FTPS pin is checked before authentication/upload;
- [x] mismatch is fail-closed and does not expose fingerprints in the normalized error;
- [x] existing `tls_verify` compatibility semantics are preserved;
- [x] automated tests cover match, mismatch and invalid fingerprint input;
- [ ] exact final-head CI for the remediation PR;
- [ ] physical X2D MQTT fingerprint validation;
- [ ] physical X2D FTPS fingerprint validation;
- [ ] decision on a default pin/TOFU enrollment UX after hardware evidence.
