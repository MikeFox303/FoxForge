# Moonraker/Klipper adapter foundation

- **Status:** production transport foundation implemented; physical validation pending
- **Updated:** 2026-09-06
- **Related:** [ADR 0001](../adr/0001-printer-adapter-architecture.md), [Moonraker HTTP/WebSocket transport](moonraker-http-transport.md)

## Purpose

Moonraker/Klipper is FoxForge's first non-Bambu adapter family and validates that common printer/fleet/queue/material contracts are genuinely vendor-independent.

## Boundary

```text
application / FleetService / QueueService
                |
      FoxForge printer contracts
                |
        MoonrakerAdapter
                |
      HTTP/WebSocket transport
                |
         Moonraker/Klipper
```

Moonraker JSON/HTTP/WebSocket DTOs do not cross into common domain/application code.

## State and material mapping

The adapter normalizes Klippy readiness plus `print_stats`/`virtual_sdcard` state into FoxForge connection, operational and job snapshots.

Moonraker exposes one stable external material source in the common v1 model:

```text
unit_id = moonraker:external:0
slot_id = moonraker:external:0:slot:0
```

It is deliberately not modeled as an AMS/CFS. Presence/activity/material identity stay unknown when Moonraker does not report them. Inventory can still associate a FoxForge spool with the opaque physical slot.

## Print execution

The common Moonraker execution capability accepts G-code, uploads to the Moonraker `gcodes` root, verifies/uses the artifact identity according to the transport contract and starts the print only after upload succeeds.

The adapter/queue boundaries preserve `INDETERMINATE` when a start side effect may have occurred but cannot be proven. Durable retry/reconciliation remains owned by `QueueService`.

## Production transport

Current source implements the HTTP/WebSocket transport foundation, including:

- configured endpoint/API-key handling;
- live initial state plus WebSocket subscription/reconciliation;
- upload/start behavior;
- common Pause/Resume/Cancel mapping;
- normalized transport errors;
- explicit resolved-address/redirect/userinfo endpoint security policy.

See [moonraker-http-transport.md](moonraker-http-transport.md) for the normative transport/security details.

## Remaining validation

Representative real Ender 3 V3 KE/OpenKE evidence is still required for:

- connect/reconnect;
- endpoint-policy compatibility on the real LAN;
- upload/checksum/start;
- Pause/Resume/Cancel;
- completion/failure;
- ambiguous-outcome handling.

## Provenance

The Moonraker adapter/transport are newly written FoxForge code based on FoxForge-owned contracts and public Moonraker protocol semantics. Direct upstream source incorporation, if ever used, must be documented separately with original copyright/license notices.
