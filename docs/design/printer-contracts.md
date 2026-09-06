# Printer contracts v1

- **Status:** implemented normative contract
- **Updated:** 2026-09-06
- **Related:** [ADR 0001](../adr/0001-printer-adapter-architecture.md), [FleetService](fleet-service.md), [job control](job-control.md)

This document describes the semantics of the implemented FoxForge printer boundary. The Python definitions under `backend/src/foxforge/domain/printers/` are the executable source of truth; this page explains the invariants application, adapter and UI code must preserve.

## Goals

The v1 contracts let fleet, queue, inventory and frontend/API layers operate without vendor protocol dependencies while allowing rich vendor extensions.

Binding rules:

1. common/domain/application code does not import Bambu or Moonraker transport DTOs;
2. the base `PrinterAdapter` remains small;
3. optional behavior is exposed through typed capabilities;
4. vendor-specific depth stays vendor-specific until a genuinely common workflow justifies promotion;
5. printer/material identifiers owned by an adapter are opaque outside that adapter;
6. reconnect/event consumers tolerate duplicate/replayed observations;
7. ambiguous physical side effects are represented explicitly rather than guessed.

## `PrinterAdapter`

The implemented base protocol owns identity, lifecycle, current normalized state, capability lookup and events:

```python
class PrinterAdapter(Protocol):
    @property
    def identity(self) -> PrinterIdentity: ...
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    def snapshot(self) -> PrinterSnapshot: ...
    def capability(self, capability_type: type[C]) -> C | None: ...
    def events(self) -> AsyncIterator[PrinterEvent]: ...
```

`identity` is available without network I/O. `connect()`/`disconnect()` are idempotent. `snapshot()` is immediate and uses adapter-owned normalized state rather than causing hidden vendor polling.

## Common state

`PrinterIdentity` carries stable FoxForge identity plus descriptive vendor/model/serial/adapter metadata. `PrinterSnapshot` contains only cross-vendor connection/operational/job/fault/freshness state.

Common snapshots must not contain raw MQTT JSON, Moonraker JSON-RPC payloads, AMS-native objects, HMS details or vendor transport exceptions.

Unknown data remains unknown rather than being fabricated. Stale data is marked stale.

## Events

`PrinterEvent` delivery is at-least-once. Ordering is meaningful within a connection epoch, not globally across reconnects/printers.

Consumers must:

- tolerate duplicate event identity;
- stop comparing sequence numbers across epochs;
- reconcile durable workflows against canonical snapshots/state;
- not infer printer-side acceptance from a progress event alone.

## Error contract

Vendor exceptions terminate at the adapter boundary and become normalized `PrinterAdapterError` values.

`INDETERMINATE` means a remote side effect may have occurred but cannot be proven. Queue/job-control callers must observe/reconcile before any new attempt; they must not convert it into an automatic retry.

## Implemented common capabilities

### `foxforge.print_execution` / v1

Represents assessment and submission of a FoxForge-managed artifact without exposing the vendor delivery protocol.

Key semantics:

- supported formats are advertised by the descriptor;
- plate selection/material bindings are capability-driven;
- physical material `slot_id` is opaque;
- queue persists `dispatch_id` before submit;
- submit returns a `PrintDispatchReceipt` only for a confirmed accepted dispatch;
- definite pre-start failures and ambiguous post-side-effect outcomes remain distinct.

Bambu may implement this through project storage + MQTT; Moonraker may implement it through upload + HTTP/WebSocket. Queue code does not know which.

### `foxforge.material_system` / v1

Represents observable physical material units/slots in a vendor-independent form.

Common state may include unit/slot identity, material/color/tag/remaining information and active source when actually reported. It does not own FoxForge spool identity.

Inventory associates a `spool_id` with `(printer_id, opaque slot_id)` separately.

Bambu AMS-family devices and external feed can map into this capability; Moonraker can expose a single external source without pretending to be an AMS.

### `foxforge.job_control` / v1

Represents Pause/Resume/Cancel for the **exact active observed vendor job**.

Controls are capability/state-gated and carry `controlId` independently from HTTP `Idempotency-Key`. A stale/mismatched vendor job must fail closed. Ambiguous control outcomes are not automatically resent.

See [job-control.md](job-control.md).

## Vendor-specific capabilities

Capabilities such as Bambu drying, HMS actions, K profiles, dual-nozzle behavior and Virtual Printer remain vendor extensions unless/until their semantics become genuinely common.

The absence of a capability is the supported-state signal. Common code must not probe by calling fake methods and catching `NotImplementedError`.

## Local artifact boundary

The current in-process runtime uses an application-managed absolute `LocalPrintArtifact.path` internally. That path never becomes a public client API: browsers stage bytes and receive an artifact identity; the server resolves its own path before calling the capability.

A future out-of-process adapter protocol may replace local-path transport without changing the higher-level print semantics.

## Architecture and acceptance

Contract changes must preserve:

- architecture tests forbidding common -> vendor imports;
- Bambu and Moonraker implementations behind the same base/capability contracts;
- exact queue dispatch/receipt/`INDETERMINATE` behavior;
- opaque material slot identity;
- normalized error/event semantics;
- capability-aware API/frontend behavior;
- separate physical validation for real printer behavior.

Breaking semantic changes require a new capability major version or an explicit ADR update; implementation details alone do not.
