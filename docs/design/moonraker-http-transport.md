# Moonraker HTTP/WebSocket transport

- **Status:** Implemented and CI validated; physical printer validation pending
- **Related:** [Moonraker adapter foundation](moonraker-adapter-foundation.md)
- **Date:** 2026-09-04

## Purpose

`MoonrakerHttpTransport` is the production wire implementation below FoxForge's `MoonrakerTransport` protocol. It translates Moonraker HTTP/WebSocket behavior into Moonraker-native DTOs without exposing Moonraker JSON, object names, URLs, or authentication details to the common printer domain or application services.

This is newly written FoxForge code based on Moonraker's public API semantics. It is not copied from Bambuddy, PrintBuddy, or PrintOps.

## Runtime dependency

FoxForge uses `aiohttp>=3.12,<4` for both HTTP and WebSocket operations. Keeping one async client stack avoids a second network dependency and works with the single-process Docker/ARM64/Umbrel deployment target.

## Configuration

`MoonrakerHttpSettings` currently accepts:

```text
base_url: absolute http:// or https:// Moonraker URL
api_key: optional Moonraker API key
request_timeout_seconds: positive timeout, default 10 seconds
```

When `api_key` is configured it is sent as `X-Api-Key` on both HTTP and WebSocket upgrade requests through the shared `aiohttp.ClientSession`.

A registry-ready factory is exported as:

```text
create_moonraker_http_adapter(identity, settings)
```

This keeps `AdapterRegistry` vendor-independent: the composition root registers the Moonraker factory rather than adding `if adapter_kind == "moonraker"` branches to the registry.

## Connection and state flow

The transport connects in this order:

```text
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

Before the print-start request, ordinary connectivity/upload failures can be normalized as unavailable/timeout/rejected and evaluated by queue policy.

After the print-start request may have reached Moonraker, the safety rule changes. A timeout, connection loss, or ambiguous server failure is reported as:

```text
MoonrakerTransportErrorKind.INDETERMINATE
```

This propagates to common `PrinterErrorCode.INDETERMINATE`. The durable queue must reconcile printer/job state before any retry, preventing a blind duplicate print.

## Test boundary

CI starts a local `aiohttp.web` Moonraker test server. The tests exercise real sockets and protocol encoding rather than mocking `aiohttp` methods:

- API-key header propagation;
- WebSocket JSON-RPC subscription;
- `notify_status_update` ingestion;
- multipart G-code upload;
- SHA-256 checksum field;
- explicit print start after successful upload;
- fail-safe `INDETERMINATE` behavior when the start response times out;
- registry-ready factory validation.

These tests validate FoxForge's transport semantics, but they do not replace hardware testing against Moonraker/OpenKE.

## Physical validation still required

The next hardware gate should run against a real Moonraker printer and verify at minimum:

1. connection to the configured host/port and authentication mode;
2. initial idle snapshot;
3. live `print_stats`/`virtual_sdcard` updates during a print;
4. reconnect after Moonraker/Klippy restart;
5. upload of a harmless known G-code artifact;
6. print start only with explicit test intent;
7. queue reconciliation after deliberately interrupted connectivity;
8. no assumptions about AMS/CFS or Bambu-specific state.

For the user's Ender-3 V3 KE/OpenKE deployment the existing Moonraker port/configuration must be confirmed at validation time rather than hard-coded into FoxForge.

## Acceptance criteria

- [x] HTTP and WebSocket details remain below `MoonrakerTransport`.
- [x] API-key authentication is supported.
- [x] initial state is reconciled before `connect()` succeeds.
- [x] live object subscriptions update complete native state.
- [x] upload carries the common artifact SHA-256 as Moonraker checksum.
- [x] upload is confirmed before an explicit start request.
- [x] ambiguous post-start failures become `INDETERMINATE`.
- [x] production adapter factory can be registered without modifying `AdapterRegistry`.
- [x] local socket-level integration tests pass on Python 3.12 and 3.13.
- [ ] physical Ender/OpenKE validation.

## Upstream protocol references

- Moonraker API: https://moonraker.readthedocs.io/en/latest/web_api/
- Moonraker external API introduction: https://moonraker.readthedocs.io/en/latest/external_api/introduction/
