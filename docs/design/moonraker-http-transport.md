# Moonraker HTTP/WebSocket transport

- **Status:** Implemented and CI validated; physical printer validation pending
- **Related:** [Moonraker adapter foundation](moonraker-adapter-foundation.md)
- **Date:** 2026-09-04

## Purpose

`MoonrakerHttpTransport` is the Moonraker wire implementation below FoxForge's `MoonrakerTransport` protocol. Production composition wraps those semantics with `MoonrakerSecuredHttpTransport`, which adds endpoint-resolution and redirect policy without exposing Moonraker JSON, object names, URLs, or authentication details to the common printer domain or application services.

This is newly written FoxForge code based on Moonraker's public API semantics. It is not copied from Bambuddy, PrintBuddy, or PrintOps.

## Runtime dependency

FoxForge uses `aiohttp>=3.12,<4` for both HTTP and WebSocket operations. Keeping one async client stack avoids a second network dependency and works with the single-process Docker/ARM64/Umbrel deployment target.

## Configuration

`MoonrakerHttpSettings` accepts:

```text
base_url: absolute http:// or https:// Moonraker URL
api_key: optional Moonraker API key
request_timeout_seconds: positive timeout, default 10 seconds
```

The production adapter factory additionally accepts these explicit advanced endpoint-policy overrides, all defaulting to `false`:

```text
allow_public_endpoint
allow_loopback_endpoint
allow_link_local_endpoint
```

When `api_key` is configured it is sent as `X-Api-Key` on both HTTP and WebSocket upgrade requests through the shared `aiohttp.ClientSession`. Credentials embedded in `base_url` userinfo are rejected; authentication must use the dedicated API-key field.

A registry-ready factory is exported as:

```text
create_moonraker_http_adapter(identity, settings)
```

This keeps `AdapterRegistry` vendor-independent: the composition root registers the Moonraker factory rather than adding `if adapter_kind == "moonraker"` branches to the registry.

## Endpoint security policy

Moonraker is intentionally a server-side connection target, so its configured URL is also an SSRF boundary. Normal LAN printers must remain usable, but FoxForge must not silently turn an operator-supplied hostname into unrestricted server-side network access.

Production composition therefore applies these rules before and during connection:

- every DNS result is validated, not only the configured hostname string;
- default allowed ranges are IPv4 RFC1918 (`10/8`, `172.16/12`, `192.168/16`) and IPv6 ULA (`fc00::/7`);
- loopback, link-local and public/global destinations require separate explicit advanced overrides;
- unspecified, multicast and reserved destinations remain rejected;
- a hostname with mixed safe and unsafe DNS results is rejected rather than selecting only the safe record;
- HTTP redirects are rejected so a permitted Moonraker origin cannot redirect FoxForge to another destination;
- the same validating resolver is supplied to the production `aiohttp` connector used by HTTP and WebSocket traffic;
- URL userinfo is rejected so credentials cannot be hidden inside an endpoint string.

The overrides are deliberately independent. For example, permitting a trusted public Moonraker endpoint does not also enable loopback or link-local access. `169.254.169.254` therefore remains blocked unless the operator explicitly enables the link-local override; that override should be treated as a high-trust deployment choice.

FoxForge does not blindly deny private address space because RFC1918/ULA networks are the normal Moonraker deployment target. Conversely, the policy does not treat Python's broad `ipaddress.is_private` classification as equivalent to a printer LAN; the allowlist is explicit.

## Connection and state flow

The transport connects in this order:

```text
validate configured/resolved endpoint
        |
        v
GET /printer/info
        |
        v
WS /websocket
        |
        v
printer.objects.subscribe
  - webhooks.state/state_message
  - print_stats.filename/print_duration/state/message
  - virtual_sdcard.progress
        |
        v
MoonrakerNativeState
        |
        v
MoonrakerAdapter mapping/events
```

If Klippy is not ready at initial connection, the transport keeps the Moonraker WebSocket session and waits for `notify_klippy_ready`. It then refreshes `/printer/info`, establishes the object subscription, and emits a reconciled native state.

`notify_status_update` payloads are deltas. The transport merges them into its adapter-owned status cache before constructing a new complete `MoonrakerNativeState`.

`notify_klippy_disconnected` represents Moonraker still being reachable while Klippy is unavailable. It therefore keeps the native Moonraker connection alive and reports Klippy as disconnected; the common adapter maps this to degraded/unknown state rather than pretending the entire host is offline.

## Print submission flow

FoxForge intentionally separates upload confirmation from the start side effect:

```text
LocalPrintArtifact (already SHA-256 verified by capability)
        |
        v
POST /server/files/upload
  root = gcodes
  checksum = artifact SHA-256
  print = false
        |
        | upload confirmed
        v
POST /printer/print/start?filename=...
        |
        v
MoonrakerNativeDispatchResult
```

If Moonraker reports that the upload itself already started printing, FoxForge does not issue a second start command.

## Failure semantics

Before the print-start request, ordinary connectivity/upload failures can be normalized as unavailable/timeout/rejected and evaluated by queue policy. Endpoint-policy failures are normalized as rejected transport errors with vendor code `endpoint_policy`.

After the print-start request may have reached Moonraker, the safety rule changes. A timeout, connection loss, or ambiguous server failure is reported as:

```text
MoonrakerTransportErrorKind.INDETERMINATE
```

This propagates to common `PrinterErrorCode.INDETERMINATE`. The durable queue must reconcile printer/job state before any retry, preventing a blind duplicate print.

## Test boundary

CI starts local `aiohttp.web` Moonraker test servers where network behavior is required. Tests cover:

- API-key header propagation;
- WebSocket JSON-RPC subscription;
- `notify_status_update` ingestion;
- multipart G-code upload;
- SHA-256 checksum field;
- explicit print start after successful upload;
- fail-safe `INDETERMINATE` behavior when the start response times out;
- registry-ready factory validation;
- RFC1918/ULA allow decisions;
- loopback/link-local/public default denial and explicit overrides;
- mixed DNS-result rejection;
- redirect rejection;
- embedded URL credential rejection.

These tests validate FoxForge's transport and endpoint-policy semantics, but they do not replace hardware testing against Moonraker/OpenKE.

## Physical validation still required

The next hardware gate should run against a real Moonraker printer and verify at minimum:

1. connection to the configured LAN host/port with the default endpoint policy;
2. authentication mode;
3. initial idle snapshot;
4. live `print_stats`/`virtual_sdcard` updates during a print;
5. reconnect after Moonraker/Klippy restart;
6. upload of a harmless known G-code artifact;
7. print start only with explicit test intent;
8. queue reconciliation after deliberately interrupted connectivity;
9. no assumptions about AMS/CFS or Bambu-specific state.

For an Ender-3 V3 KE/OpenKE deployment the actual Moonraker port/configuration must be confirmed at validation time rather than hard-coded into FoxForge.

## Acceptance criteria

- [x] HTTP and WebSocket details remain below `MoonrakerTransport`.
- [x] API-key authentication is supported.
- [x] initial state is reconciled before `connect()` succeeds.
- [x] live object subscriptions update complete native state.
- [x] upload carries the common artifact SHA-256 as Moonraker checksum.
- [x] upload is confirmed before an explicit start request.
- [x] ambiguous post-start failures become `INDETERMINATE`.
- [x] production adapter factory can be registered without modifying `AdapterRegistry`.
- [x] production endpoint policy preserves RFC1918/ULA LAN targets while blocking unsafe destinations by default.
- [x] every resolved address is validated and mixed safe/unsafe DNS answers fail closed.
- [x] redirects and URL userinfo are rejected.
- [x] exceptional public/loopback/link-local targets require explicit independent overrides.
- [ ] exact final-head Python 3.12/3.13, container, browser and security CI after AUD-014 changes.
- [ ] physical Ender/OpenKE validation.

## Upstream protocol references

- Moonraker API: https://moonraker.readthedocs.io/en/latest/web_api/
- Moonraker external API introduction: https://moonraker.readthedocs.io/en/latest/external_api/introduction/
