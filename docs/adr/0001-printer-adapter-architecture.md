# ADR 0001: PrinterAdapter architecture

- **Status:** Accepted and implemented as the core printer boundary
- **Date:** 2026-09-03
- **Implementation update:** 2026-09-06
- **Decision owners:** FoxForge maintainers

## Context

FoxForge must manage multiple printer vendors without reducing rich platforms—especially Bambu Lab—to a lowest-common-denominator interface. It must also remain practical for Docker, ARM64 and Umbrel.

Upstream projects provide complementary reference points:

- **Bambuddy** — deep Bambu behavior and product workflows;
- **PrintBuddy** — provider/multi-vendor isolation ideas;
- **PrintOps** — higher-level farm/operations domain separation.

FoxForge must not let common queue, inventory, fleet or API code depend directly on Bambu MQTT/AMS types or Moonraker JSON.

## Decision

FoxForge uses a **ports-and-adapters architecture** for printer integrations.

> **Normalize what is genuinely common; preserve what is genuinely vendor-specific.**

### Common printer domain

FoxForge owns vendor-neutral printer identity, normalized connection/operational/job state, common faults/events and capability descriptors. Vendor protocol/state values are mapped inside the adapter boundary.

### Small `PrinterAdapter`

The base adapter owns lifecycle and observation:

```text
identity
connect / disconnect
snapshot
event stream
capability discovery
```

It does not grow one method per vendor feature.

### Typed capabilities

Common semantics live behind typed capabilities such as print execution, job control and material-system observation. Application services depend on the capability they need, not a concrete adapter.

Deep vendor features remain typed vendor extensions. Bambu drying, HMS, K profiles, dual-nozzle behavior, Virtual Printer and similar features must not force non-Bambu adapters to emulate Bambu concepts.

### Material systems

The common material model describes units, slots, active source and observable material state. Bambu AMS/AMS 2 Pro/AMS HT, Creality CFS and external spools may fit the common observation model, while vendor-only operations stay vendor-specific.

Inventory owns FoxForge spool identity; printer material snapshots expose physical source/slot identity only.

### Transport separation

An adapter may compose multiple transports. Transport clients are infrastructure, not the application adapter itself.

```text
BambuAdapter -> MQTT/TLS + project storage/FTPS + discovery + future Bambu extensions
MoonrakerAdapter -> HTTP + WebSocket
```

### Registry/composition

Vendor selection belongs to the composition root/`AdapterRegistry`. `FleetService`, queue and inventory code receive already-created `PrinterAdapter` instances and contain no vendor selection branches.

### Events

Adapters publish normalized events with per-connection epoch/ordering semantics. Vendor-specific events may exist under explicit extension contracts. Queue/inventory consumers must remain idempotent across reconnect/replay.

### Promotion-to-common rule

A vendor feature becomes a common capability only when a vendor-independent FoxForge workflow needs it and its semantics can be defined without modeling one vendor's implementation.

## Implementation state

The decision is no longer a bootstrap plan. Current source implements:

- FoxForge-owned printer contracts and architecture guards;
- Bambu and Moonraker adapters;
- `AdapterRegistry` and dynamic `FleetService`;
- durable queue through common `PrintExecutionCapability`;
- common `JobControlCapability`;
- common `MaterialSystemCapability`;
- Bambu AMS/external and Moonraker external-source observation;
- capability-driven API/UI;
- vendor-independent reconnect supervision;
- Bambu LAN discovery as infrastructure feeding normal authenticated setup.

Physical validation and deeper vendor extensions remain ongoing, but the dependency direction itself is established.

## Alternatives rejected

- **Bambu-centric common core:** spreads Bambu assumptions into every new vendor.
- **Bambu-shaped provider protocol:** still forces other vendors to populate Bambu-oriented concepts.
- **One giant optional-method adapter:** weak interface segregation and capability discovery.
- **Generic string command API:** loses type safety and moves contracts into runtime string conventions.
- **One microservice per vendor today:** unnecessary deployment/network/memory complexity for the current Raspberry Pi/Umbrel scale; the in-process boundary does not prevent a future out-of-process protocol.

## Consequences

Positive:

- queue/fleet/inventory remain genuinely multi-vendor;
- deep Bambu work remains first-class;
- protocol churn is isolated behind adapters;
- common contract tests and architecture guards are possible;
- one Docker/Umbrel runtime remains sufficient.

Costs:

- explicit mapping/domain types are required;
- frontend/API must be capability-aware;
- common-vs-vendor classification requires deliberate review.

## Acceptance criteria

- common/domain/application packages do not import vendor transports/DTOs;
- Bambu and Moonraker coexist through common fleet/queue services;
- adding a third adapter using existing capabilities does not require vendor branches in core services;
- deep Bambu behavior can grow without polluting base snapshots;
- reconnect/event/queue semantics remain safe under duplicate/late/restart scenarios;
- Docker `amd64`/`arm64` and Umbrel remain compatible with the adapter model.
