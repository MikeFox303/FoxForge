# Moonraker/Klipper adapter foundation

- **Status:** Implemented foundation; production wire transport pending
- **Related ADR:** [ADR 0001: PrinterAdapter architecture](../adr/0001-printer-adapter-architecture.md)
- **Common contracts:** [Printer contracts v1](printer-contracts.md)
- **Date:** 2026-09-04

## Purpose

This design records the Phase 5 boundary for FoxForge's second real printer adapter family. Moonraker/Klipper support must prove that the common printer contracts are genuinely vendor-independent while avoiding fake AMS/Bambu semantics on printers that do not expose them.

## Dependency boundary

```text
FoxForge application / FleetService / QueueService
                |
                v
      foxforge.domain.printers
                ^
                |
 foxforge.adapters.moonraker
                |
                v
       MoonrakerTransport
                |
        future HTTP/WebSocket
```

`foxforge.adapters.moonraker` is an anti-corruption layer. Moonraker JSON-RPC/HTTP objects, Klipper object names, file APIs and WebSocket notification payloads must not cross into `foxforge.domain.printers` or application code.

## Native state

`MoonrakerNativeState` currently models only the information required by common contracts:

- Moonraker/Klippy connectivity and Klippy state/message;
- `print_stats` state and filename;
- virtual SD progress;
- print duration and print message;
- observation timestamp.

The production wire transport should obtain the initial state from Moonraker webhooks/printer-object queries and keep it current through Moonraker object subscriptions. The adapter itself consumes only `MoonrakerTransport` and therefore remains testable without network access.

## Common snapshot mapping

- disconnected transport -> common `DISCONNECTED/OFFLINE`;
- Klippy `ready` + `standby` -> `CONNECTED/IDLE`;
- `printing` -> `PRINTING` job and printer state;
- `paused` -> `PAUSED`;
- `complete` -> completed job;
- Klippy `shutdown`/`error` -> degraded connection plus normalized common fault summary;
- Moonraker/Klipper diagnostic details remain vendor-local and may later be exposed through typed extension capabilities.

Moonraker filename is used as the v1 opaque vendor job identifier because Moonraker does not provide a Bambu-style job id for this flow.

## Material system semantics

Moonraker v1 exposes one stable external material source:

```text
unit_id = moonraker:external:0
slot_id = moonraker:external:0:slot:0
```

This is intentionally **not** a fabricated AMS/CFS. `MaterialSystemDescriptor` reports that active source, remaining fraction, material identity and tag identity are not observable. Presence/activity therefore remain `UNKNOWN`.

The stable slot id still lets FoxForge inventory persist:

```text
(printer_id, slot_id) -> spool_id
```

and lets queue requests bind logical material index 0 to the physical external source.

## Print execution semantics

The first Moonraker print capability accepts only common `GCODE` artifacts.

- plate selection is unsupported;
- one logical material input may bind to the stable external slot;
- assessment verifies connectivity/readiness plus an unchanged readable local artifact;
- the adapter converts the common request to `MoonrakerNativePrintRequest` containing local path, filename and SHA-256;
- the future concrete transport owns Moonraker upload and `printer.print.start` details;
- confirmed `dispatch_id` values are cached per adapter instance for common idempotency semantics;
- durable idempotency across process restarts remains owned by `QueueService`/`QueueStore`.

## Error boundary

`MoonrakerTransportErrorKind` maps to the common `PrinterAdapterError` taxonomy. In particular, a timeout/disconnect after the start side effect when acceptance cannot be proven must surface as `INDETERMINATE`, allowing the durable queue to require reconciliation instead of blindly starting a duplicate job.

## Production wire transport — next slice

The concrete transport should use official Moonraker semantics rather than leaking them upward:

1. connect/authenticate to the configured Moonraker endpoint;
2. read webhooks/Klippy readiness;
3. query and subscribe to `print_stats` and `virtual_sdcard` state;
4. upload G-code into Moonraker's `gcodes` root while checking the artifact fingerprint;
5. request `printer.print.start` only after upload success;
6. translate HTTP/JSON-RPC/WebSocket failures into `MoonrakerTransportError`;
7. reconnect and publish a reconciled full native state before resuming incremental events.

## Acceptance criteria for the foundation

- [x] no Moonraker JSON/API DTO leaks into common domain/application code;
- [x] normalized offline/idle/printing/paused/completed/failure mapping;
- [x] stable single external material slot without AMS emulation;
- [x] common G-code `PrintExecutionCapability`;
- [x] unsupported plate/material selections fail through common blockers;
- [x] adapter lifecycle is idempotent;
- [x] adapter events preserve per-connection epochs and normalized ordering;
- [x] transport errors, including `INDETERMINATE`, are normalized;
- [ ] production HTTP/WebSocket transport and hardware validation;
- [ ] real Ender/OpenKE integration smoke test.

## Provenance

The files under `src/foxforge/adapters/moonraker/` are newly written FoxForge code. The implementation follows FoxForge-owned contracts and public Moonraker protocol semantics; it is not copied from Bambuddy, PrintBuddy or PrintOps. Any future direct incorporation of upstream source must be documented separately with its original copyright/license notices.
