# Bambu adapter foundation

- **Status:** Implemented foundation
- **Related ADR:** [ADR 0001: PrinterAdapter architecture](../adr/0001-printer-adapter-architecture.md)
- **Related common contracts:** [Printer contracts v1](printer-contracts.md)
- **Date:** 2026-09-03

## Purpose

This document records the first Bambu-specific implementation slice built on top of the vendor-neutral FoxForge printer contracts.

The goal is to prove the anti-corruption boundary before FoxForge connects concrete MQTT, project-storage, cloud, camera, or other Bambu-specific transports.

## Provenance

The code under `src/foxforge/adapters/bambu/` in this foundation is newly written FoxForge code.

Its behavior and field selection are informed by public Bambu/Bambuddy behavior, especially the upstream Bambuddy MQTT/printer-manager implementation:

- https://github.com/maziggy/bambuddy
- upstream Bambu MQTT state and command handling in `backend/app/services/bambu_mqtt.py`
- upstream printer lifecycle/state usage in `backend/app/services/printer_manager.py`

No Bambuddy source file is copied into this adapter foundation.

A former X2D port-6000 experiment was kept temporarily under `integrations/bambuddy/` during early migration work but was removed from the current tree on 2026-09-04. FoxForge will not promote that implementation. Future X2D/eMMC support, if required, will be newly written behind the Bambu-specific project-storage boundary after physical validation, with provenance documented for the implementation actually adopted.

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
        +-- LAN MQTT transport
        +-- BambuProjectStorage strategies
        +-- future cloud/camera transports
        `-- future validated X2D/eMMC storage strategy
```

The application layer never receives `BambuNativeState`, AMS ids, tray ids, Bambu gcode-state strings, or Bambu transport exceptions.

## Native DTO boundary

`src/foxforge/adapters/bambu/native.py` contains Bambu-only transport DTOs such as:

- `BambuNativeState`
- `BambuNativeMaterialUnit`
- `BambuNativeTray`
- `BambuNativePrintRequest`
- `BambuNativeMaterialRoute`

These types are legal inside `foxforge.adapters.bambu` and concrete Bambu transport modules. They MUST NOT be imported by `foxforge.domain` or vendor-neutral application services.

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

AMS, AMS 2 Pro, and AMS HT currently map to common `MaterialUnitKind.MULTI_SLOT`; external feed maps to `EXTERNAL`. Rich Bambu-only operations such as drying, filament backup, RFID-specific commands, and K-profile operations remain Bambu extension capabilities.

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

The capability does not know whether project delivery uses standard FTPS, a future X2D internal-eMMC strategy, cloud, or another Bambu-specific mechanism.

## `INDETERMINATE` semantics

If the transport cannot prove whether a side-effecting start request was accepted, it raises a Bambu-native `INDETERMINATE` error which becomes common `PrinterErrorCode.INDETERMINATE`.

The capability does not add a vendor-specific reconciliation method to the common contract. The queue owns durable reconciliation and retry policy as specified in Printer contracts v1. Confirmed receipts are cached; ambiguous outcomes are not misrepresented as confirmed success.

## Current and future scope

The foundation has since been extended with production-oriented LAN MQTT/TLS, standard FTPS project storage, the `BambuProjectStorage` seam, and production composition factories.

Still outside the implemented production surface:

- physically validated X2D/eMMC-specific project storage;
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

## Next Bambu implementation principle

New Bambu features should extend the existing typed adapter boundaries rather than reintroducing preserved experimental integration code. In particular, any X2D-specific storage behavior should be discovered on hardware and then implemented as a production `BambuProjectStorage` strategy with acceptance tests and explicit provenance.
