# AdapterRegistry and FleetService

- **Status:** implemented and dynamically composed
- **Updated:** 2026-09-06
- **Related:** ADR 0001, [reconnect supervision](reconnect-supervision.md)

## Purpose

`AdapterRegistry` and `FleetService` keep vendor selection out of common application workflows while allowing multiple printer families to coexist in one runtime.

```text
composition root
      |
AdapterRegistry -> creates PrinterAdapter instances
      |
FleetService
      |
normalized snapshots / events / typed capabilities
```

## AdapterRegistry

The registry maps persisted `adapter_kind` values to externally registered factories. It does not import concrete Bambu/Moonraker adapters itself.

Factories receive `PrinterIdentity` plus vendor-owned settings and must return an adapter with the requested identity. Unknown kinds, duplicate registration and identity mismatch are explicit errors.

## FleetService

Current service responsibilities include:

- deterministic printer identity/snapshot enumeration;
- capability lookup;
- connect/disconnect per printer and fleet-wide lifecycle;
- merged normalized event fan-out;
- dynamic adapter add/remove used by application-managed printer setup;
- preservation of per-adapter event epoch/sequence semantics.

`FleetService` does not expose raw vendor state and contains no Bambu/Moonraker selection branches.

## Dynamic configuration

The original fixed-fleet bootstrap has evolved into runtime composition:

- Add Printer preflights and then attaches a new adapter;
- Update may replace an adapter while preserving rollback safety;
- Remove detaches it;
- reconnect supervision discovers configured fleet changes and maintains independent workers.

Persistence/credential handling remains outside `FleetService` in the runtime printer manager and SecretStore boundary.

## Event semantics

Fleet subscriptions receive normalized `PrinterEvent` values with printer ID, connection epoch, sequence and timestamp preserved. Ordering is per adapter/connection epoch; no global total ordering across printers is implied.

Relay subscription is established before connect operations where required so initial connection/reconciliation events are not lost.

## Error boundary

Unknown printer IDs are application errors. Transport failures must already be normalized by the adapter boundary; raw vendor exceptions do not become fleet-domain contracts.

## Acceptance criteria

- registry/application code has no concrete vendor imports;
- mixed Bambu/Moonraker/fake adapters can coexist;
- dynamic add/remove does not require vendor branches in `FleetService`;
- normalized events/capabilities remain the only application-facing printer surface;
- reconnect supervision can operate per printer without owning vendor protocols;
- architecture tests continue to forbid common -> vendor dependency direction.
