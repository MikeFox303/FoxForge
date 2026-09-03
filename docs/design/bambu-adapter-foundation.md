# Bambu adapter foundation

- **Status:** Implemented foundation
- **Related ADR:** [ADR 0001: PrinterAdapter architecture](../adr/0001-printer-adapter-architecture.md)
- **Related common contracts:** [Printer contracts v1](printer-contracts.md)
- **Date:** 2026-09-03

## Purpose

This document records the first Bambu-specific implementation slice built on top of the vendor-neutral FoxForge printer contracts.

The goal is to prove the anti-corruption boundary before FoxForge connects real MQTT, FTP, cloud, camera, or X2D port-6000 transports.

## Provenance

The code under `src/foxforge/adapters/bambu/` in this foundation is newly written FoxForge code.

Its behavior and field selection are informed by public Bambu/Bambuddy behavior, especially the upstream Bambuddy MQTT/printer-manager implementation:

- https://github.com/maziggy/bambuddy
- upstream Bambu MQTT state and command handling in `backend/app/services/bambu_mqtt.py`
- upstream printer lifecycle/state usage in `backend/app/services/printer_manager.py`

No Bambuddy source file is copied into this adapter foundation.

FoxForge also preserves a separate X2D `BambuTunnelLocal :6000` experiment under `integrations/bambuddy/x2d_port6000/`. That implementation has its own provenance notice because it was derived from AGPL-compatible reverse-engineering work in `ClusterM/open-bamboo-networking`. It remains intentionally isolated from print dispatch until hardware validation is complete.

## Layering

```text
FoxForge application/domain
        |
        v
PrinterAdapter + common capabilities
        |
        v
BambuAdapter
  |-- BambuPrintExecutionCapability
  |-- BambuMaterialSystemCapability
        |
        v
BambuTransport protocol
        |
        +-- future MQTT transport
        +-- future FTP/internal-storage transport
        +-- future cloud/camera transports
        +-- future validated X2D BambuTunnelLocal integration
```

The application layer never receives `BambuNativeState`, AMS ids, tray ids, Bambu gcode-state strings, or Bambu transport exceptions.

## Native DTO boundary

`src/foxforge/adapters/bambu/native.py` contains Bambu-only transport DTOs such as:

- `BambuNativeState`
- `BambuNativeMaterialUnit`
- `BambuNativeTray`
- `BambuNativePrintRequest`
- `BambuNativeMaterialRoute`

These types are legal inside `foxforge.adapters.bambu` and concrete Bambu transport packages. They MUST NOT be imported by `foxforge.domain` or vendor-neutral application services.

## State mapping

The foundation maps Bambu gcode-state values into FoxForge states at the adapter boundary.

Examples:

```text
Bambu IDLE      -> FoxForge IDLE
Bambu PREPARE   -> FoxForge PREPARING
Bambu SLICING   -> FoxForge PREPARING
Bambu RUNNING   -> FoxForge PRINTING
Bambu PAUSE     -> FoxForge PAUSED
Bambu FINISH    -> FoxForge COMPLETED
Bambu FAILED    -> FoxForge FAILED
```

A disconnected native state always becomes `ConnectionState.DISCONNECTED` + `OperationalState.OFFLINE`.

Bambu progress percentages are normalized to `0.0..1.0`; remaining minutes become seconds. Invalid negative/sentinel values become `None` rather than crossing into the common domain.

## Material-system mapping

Bambu AMS-family units are exposed through `MaterialSystemCapability` rather than through an AMS-shaped common model.

Example physical identity:

```text
Bambu ams_id=0, tray_id=1
        |
        v
opaque common slot id:
bambu:unit:0:tray:1
```

Only the Bambu adapter parses or constructs this value. Common code treats it as an opaque `MaterialSlotId`.

AMS, AMS 2 Pro, and AMS HT currently map to common `MaterialUnitKind.MULTI_SLOT`; external feed maps to `EXTERNAL`. Rich Bambu-only operations such as drying, filament backup, RFID-specific commands, and K-profile operations remain future Bambu extension capabilities.

Inventory `spool_id` remains outside the adapter exactly as required by Printer contracts v1.

## Print execution mapping

`BambuPrintExecutionCapability` implements common `PrintExecutionCapability` with the following v1 behavior:

- accepts 3MF artifacts;
- supports common zero-based plate selection;
- converts a selected common plate index to the Bambu-native one-based plate number at the adapter boundary;
- resolves opaque FoxForge material slot ids back to Bambu `(ams_id, tray_id)` routes;
- delegates actual delivery/start behavior to `BambuTransport.submit_print()`;
- caches only confirmed `PrintDispatchReceipt` values for in-process idempotency;
- translates Bambu transport errors into normalized `PrinterAdapterError` codes.

The capability does not know whether the eventual transport uses legacy FTP, X2D internal eMMC transfer, MQTT, cloud, or another Bambu-specific mechanism.

## `INDETERMINATE` semantics

If the transport cannot prove whether a side-effecting start request was accepted, it raises a Bambu-native `INDETERMINATE` error which becomes common `PrinterErrorCode.INDETERMINATE`.

The capability does not add a vendor-specific reconciliation method to the common contract. The future queue owns durable reconciliation and retry policy as specified in Printer contracts v1. Confirmed receipts are cached; ambiguous outcomes are not misrepresented as confirmed success.

## Deliberately out of scope

This foundation does **not** yet provide:

- real Paho MQTT connectivity;
- real Bambu FTP/FTPS uploads;
- production X2D `:6000` uploads;
- cloud authentication;
- camera transport;
- HMS detail capability;
- AMS drying controls;
- K profiles/calibration;
- dual-nozzle controls;
- Virtual Printer behavior.

Those features belong below or beside the adapter boundary and should be added incrementally with hardware/protocol tests.

## Acceptance criteria

The foundation is acceptable when:

1. Bambu-native state maps to FoxForge snapshots without changing common domain types.
2. `BambuAdapter` implements idempotent connect/disconnect and normalized event delivery over an injected transport.
3. The adapter exposes common `PrintExecutionCapability` and `MaterialSystemCapability`.
4. A zero-based common plate selection is translated at the Bambu boundary.
5. Opaque common material slot ids resolve to Bambu AMS/tray routes only inside the adapter package.
6. Confirmed duplicate dispatch ids do not intentionally start a second print.
7. Bambu transport errors are normalized and do not escape to common application code.
8. Existing common printer contract tests remain green.
9. Python 3.12 and 3.13 CI plus Ruff remain green.

## Next implementation step

After this foundation is stable, the next Bambu work should implement a concrete LAN transport composition behind `BambuTransport`, starting with state ingestion and command dispatch while keeping file-transfer strategy pluggable. The X2D `BambuTunnelLocal :6000` path should only be promoted from `integrations/` after hardware validation proves the upload and print-start sequence end to end.
