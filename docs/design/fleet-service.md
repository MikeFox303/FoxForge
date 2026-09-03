# AdapterRegistry and FleetService

- **Status:** implementation design
- **Date:** 2026-09-03
- **Related:** ADR 0001

## Purpose

Phase 3 introduces the first application layer above `PrinterAdapter`. Its job is to prove that FoxForge can manage different adapter implementations without introducing vendor selection or vendor DTOs into application code.

Two components have deliberately different responsibilities:

```text
composition root / infrastructure
        |
        v
AdapterRegistry
        |
        | creates PrinterAdapter instances
        v
application
FleetService
        |
        v
PrinterAdapter + normalized snapshots/events/capabilities
```

## AdapterRegistry

`AdapterRegistry` maps a persisted `PrinterIdentity.adapter_kind` to a factory registered by the composition root.

The registry itself must not import `BambuAdapter`, `MoonrakerAdapter`, or any other concrete vendor adapter. Registration happens externally, for example:

```python
registry.register("bambu", make_bambu_adapter)
registry.register("moonraker", make_moonraker_adapter)
```

The factory receives the `PrinterIdentity` and an opaque settings mapping. Vendor-specific configuration parsing belongs inside the registered factory/infrastructure path, not in `FleetService`.

The registry rejects:

- unknown adapter kinds;
- duplicate registrations unless replacement is explicit;
- factories that return an adapter with a different identity than requested.

## FleetService

`FleetService` receives already-created `PrinterAdapter` instances. It does not know how they were constructed and must not contain code such as:

```python
if adapter_kind == "bambu":
    ...
elif adapter_kind == "moonraker":
    ...
```

The initial service provides:

- deterministic fleet identity enumeration;
- normalized snapshot lookup;
- typed capability lookup per printer;
- connect/disconnect for one printer;
- connect/disconnect for the whole fleet;
- one merged normalized `PrinterEvent` stream covering every adapter in the fleet.

The service intentionally does not expose raw vendor state.

## Event semantics

Fleet event subscriptions are fan-out subscriptions. A consumer receives the original normalized `PrinterEvent` emitted by the adapter; `printer_id`, `connection_epoch`, `sequence`, and timestamps are preserved.

Fleet-managed connect operations ensure per-adapter relay subscriptions are ready before calling `adapter.connect()`. This prevents startup events such as `connection_changed` or `snapshot_reconciled` from being lost because the event relay had not subscribed yet.

`FleetService` does not currently reorder events between printers. Ordering guarantees remain per adapter/connection epoch, as defined by the printer contracts. Consumers must not infer a global total order across multiple printers.

## Fixed fleet scope for v1

The first implementation treats the set of adapters passed to the constructor as fixed for the lifetime of the service. Dynamic add/remove, persisted printer CRUD, automatic reconnect policy, and health supervision are intentionally deferred until the common fleet behavior is proven.

This keeps Phase 3 focused on dependency direction rather than persistence or API design.

## Error boundaries

Unknown printer IDs raise an explicit application-level `FleetPrinterNotFoundError`.

Duplicate printer IDs are rejected at service construction.

Adapter lifecycle failures are not translated into vendor-specific application errors; concrete adapters are expected to normalize their transport failures to the common adapter error model before they reach the fleet layer.

## Architecture invariants

CI must enforce:

```text
application -> domain printer contracts        allowed
application -> concrete vendor adapter         forbidden
registry    -> domain printer contracts        allowed
registry    -> concrete vendor adapter         forbidden
adapters.*  -> domain printer contracts        allowed
```

Tests are allowed to instantiate concrete adapters to prove mixed-fleet behavior.

## Acceptance criteria

Phase 3 is complete when:

1. `AdapterRegistry` can create adapters using registered factories without vendor branches in the registry.
2. Unknown kinds, duplicate factory registration, and identity mismatches are tested.
3. `FleetService` can host at least one `FakePrinterAdapter` and one `BambuAdapter` simultaneously.
4. Both adapters can be connected/disconnected through the same fleet methods.
5. Fleet snapshot and capability lookup use only common FoxForge contracts.
6. One fleet event subscription can receive normalized events originating from both adapters.
7. Application source code has no imports from `foxforge.adapters` and no Bambu/Moonraker-specific imports.
8. Ruff and the full test suite pass on Python 3.12 and 3.13.

## Next phase

Phase 4 will route queue dispatch through `PrintExecutionCapability` obtained from `FleetService`. Queue code must not perform Bambu MQTT/FTP or future Moonraker HTTP/WebSocket operations directly.
