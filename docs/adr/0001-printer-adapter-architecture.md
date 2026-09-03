# ADR 0001: PrinterAdapter architecture

- **Status:** Accepted
- **Date:** 2026-09-03
- **Decision owners:** FoxForge maintainers
- **Scope:** Printer integration boundary, common printer domain, vendor-specific extensions

## Context

FoxForge is intended to manage printers from multiple vendors while retaining deep support for platforms whose APIs expose significantly richer behavior, especially Bambu Lab. The project also needs to remain practical for self-hosted Docker, ARM64, and Umbrel deployments.

The current FoxForge repository does not yet contain a production printer-management core. Bambuddy production remains upstream, while preserved X2D integration experiments live under `integrations/bambuddy/`. This gives FoxForge an opportunity to define the printer boundary before vendor-specific assumptions become embedded in fleet, queue, inventory, or API code.

Three upstream projects were studied for how they separate common and printer-specific logic.

### Bambuddy

Bambuddy is intentionally Bambu-native. Its printer manager directly depends on the Bambu MQTT client and Bambu printer state types, while model- and firmware-specific behavior such as chamber sensing/heating, airduct behavior, AMS drying, HMS, K profiles, and model quirks is handled close to the printer-management core.

This is appropriate for a Bambu-focused application and is valuable reference material for deep Bambu behavior, but it is not an appropriate dependency direction for FoxForge's multi-vendor core.

Reference:
- https://github.com/maziggy/bambuddy

### PrintBuddy

PrintBuddy introduces a provider boundary with `printer_providers/`, a provider factory, and implementations for Bambu, Moonraker/Klipper, Prusa, and Elegoo.

This is a useful structural step, but its provider protocol is explicitly shaped around the subset of the existing Bambu client used by its manager. As a result, non-Bambu providers can still carry Bambu-oriented state concepts and the shared printer manager remains aware of Bambu types.

FoxForge should retain the provider registry/factory idea but should not use the Bambu client surface as the common printer contract.

Reference:
- https://github.com/vmhomelab/printbuddy

### PrintOps

PrintOps demonstrates strong separation between printer operations and higher-level operational domains such as projects, warehouse, costing, customers, orders, and documents. However, its printer core and scheduler remain Bambu-native and directly depend on Bambu MQTT/FTP and Bambu feature checks.

FoxForge should retain this domain separation while introducing a stronger vendor boundary underneath printer operations.

Reference:
- https://github.com/ichwars/PrintOps

### Architectural problem

The following dependency directions must be avoided:

```text
QueueService     -> BambuMQTTClient
InventoryService -> AMSState
FleetService     -> Moonraker JSON
API              -> if model == "X2D"
```

They make each additional vendor more expensive and encourage non-Bambu printers to emulate Bambu concepts.

At the same time, FoxForge must not solve multi-vendor support by reducing every printer to a lowest-common-denominator interface. Unique Bambu functionality such as AMS/AMS 2 Pro behavior, drying, HMS, K profiles, dual-nozzle control, Virtual Printer, and X2D-specific transport must remain first-class functionality.

## Decision

FoxForge will use a **ports-and-adapters architecture** for printer integrations.

A small, vendor-neutral `PrinterAdapter` contract will form the boundary between application/domain logic and printer-specific implementations. Functionality beyond the adapter lifecycle and normalized state will be exposed through **typed capabilities**.

The governing principle is:

> Normalize what is genuinely common; preserve what is genuinely vendor-specific.

### 1. FoxForge owns the common printer domain

Common application code will use FoxForge-owned types for printer identity, connection state, operational state, active-job state, capabilities, and normalized events.

Vendor state strings and protocol DTOs must be mapped inside the adapter boundary.

For example, FoxForge operational states may include:

```text
OFFLINE
IDLE
PREPARING
PRINTING
PAUSED
COMPLETED
FAILED
CANCELLING
UNKNOWN
```

Bambu, Moonraker, Prusa, or other native states are translated to these values inside their adapters.

Raw vendor payloads may be retained for diagnostics inside infrastructure packages, but they are not part of the common domain contract.

### 2. `PrinterAdapter` remains deliberately small

The base adapter represents the lifecycle and observable state of one printer resource. It provides:

```text
identity
connect / disconnect
snapshot
normalized event stream
capability discovery
```

It does not directly grow methods for every vendor feature.

### 3. Printer operations are exposed through typed capabilities

Common capabilities will represent semantics that can be described without vendor knowledge, for example:

```text
PrintExecutionCapability
JobControlCapability
FileStorageCapability
MaterialSystemCapability
ThermalCapability
CameraCapability
LightingCapability
```

Application services depend on the capabilities they need rather than on a concrete vendor adapter.

A printer that participates in queue dispatch must expose `PrintExecutionCapability`. A read-only integration can exist without it.

### 4. Bambu-specific features remain Bambu-specific capabilities

FoxForge will not force unique Bambu functionality into generic contracts merely for symmetry. Bambu adapters may expose extension capabilities such as:

```text
BambuAmsCapability
BambuDryingCapability
BambuCalibrationCapability
BambuKProfileCapability
BambuHmsCapability
BambuDualNozzleCapability
BambuVirtualPrinterCapability
BambuCloudCapability
```

The exact extension split may evolve, but these features must not pollute the base `PrinterAdapter` or require non-Bambu adapters to emulate them.

### 5. Material systems are normalized at the slot/source level, not at the AMS level

The common material abstraction will model concepts such as:

```text
material system
material unit
slot
loaded material/spool
active source
slot state
```

This can cover Bambu AMS/AMS 2 Pro/AMS HT, Creality CFS, external spools, and future systems.

Bambu RFID metadata, AMS drying, filament-backup behavior, K-profile assignment, and other Bambu-specific semantics remain in Bambu extensions unless later proven to have a genuinely common meaning across vendors.

### 6. Transport clients and adapters are separate layers

A transport implementation is not itself the application adapter.

For Bambu, one adapter may compose multiple transports:

```text
BambuAdapter
  -> MQTT transport
  -> FTP transport
  -> Cloud transport
  -> camera transport
  -> X2D/BambuTunnelLocal transport
```

For Moonraker:

```text
MoonrakerAdapter
  -> HTTP client
  -> WebSocket client
  -> camera endpoint discovery
```

This separation allows protocol parsing, vendor mapping, adapter contracts, and application workflows to be tested independently.

### 7. Adapter creation is handled by a registry/factory in the composition root

Application code must not contain vendor-selection branches such as:

```text
if provider == "bambu": ...
elif provider == "moonraker": ...
```

An infrastructure-level `AdapterRegistry` maps persisted adapter kinds to adapter factories. `FleetService` and other application services receive already-created `PrinterAdapter` instances.

### 8. Events are part of the contract

Adapters publish normalized events such as:

```text
ConnectionChanged
PrinterStateChanged
JobStateChanged
JobProgressChanged
CapabilityChanged
MaterialSlotsChanged
```

Vendor-specific events may also exist under namespaced extension contracts, for example:

```text
bambu.hms_changed
bambu.ams_drying_changed
moonraker.object_excluded
```

Reconnect and replay behavior must be designed so queue and inventory consumers can process events idempotently.

### 9. Common and vendor-specific API surfaces may coexist

FoxForge may expose common endpoints for normalized capabilities and separate vendor extension endpoints where necessary.

A richer X2D UI is desirable and must not require adding fake fields or unsupported controls to Moonraker or other printers.

### 10. Promotion-to-common rule

A vendor feature should be promoted into a common capability only when both conditions hold:

1. a vendor-independent FoxForge workflow needs it; and
2. its semantics can be defined without naming or modeling one vendor's implementation.

Natural implementations by two or more adapters are a strong signal that a concept may belong in the common layer, but this is guidance rather than a hard numeric rule.

## Alternatives

### Alternative A: Bambu-centric core with vendor conditionals

Keep a Bambuddy-style `PrinterManager -> BambuMQTTClient` core and add other vendors with provider checks.

**Rejected because:** queue, inventory, and fleet logic would accumulate Bambu assumptions; Moonraker would tend to emulate Bambu state; vendor branching would spread across the application.

### Alternative B: Bambu-shaped provider protocol

Adopt a PrintBuddy-style provider layer while keeping the common client protocol compatible with the current Bambu client.

**Rejected as the target architecture because:** it is useful as a transition strategy but still encourages non-Bambu implementations to populate Bambu-oriented fields and preserves Bambu types in shared code.

### Alternative C: One large adapter with optional methods

Create a single interface containing printing, AMS, drying, camera, macros, calibration, lighting, and all other operations, with unsupported methods returning an error.

**Rejected because:** the interface would grow continuously, violate interface segregation, make capability discovery weak, and expose vendor concepts to every adapter.

### Alternative D: Generic string command API

Expose operations through an API such as `execute("ams.start_drying", payload)`.

**Rejected for normal application flows because:** it loses type safety, hides contracts in string conventions, weakens introspection, and moves failures to runtime. A diagnostic/debug escape hatch may be considered separately.

### Alternative E: One microservice per vendor

Run Bambu, Moonraker, Prusa, and other adapters as separate services.

**Deferred because:** it adds deployment, networking, memory, and upgrade complexity that is undesirable for Docker, ARM64, Raspberry Pi, and Umbrel at the current project scale. The in-process contract should not prevent a future out-of-process adapter protocol.

## Consequences

### Positive

- Fleet, queue, inventory, and history can be genuinely multi-vendor.
- New printer families do not require changing core workflows when existing capabilities are sufficient.
- Moonraker does not need to pretend to be Bambu.
- Deep Bambu functionality remains first-class instead of being reduced to a lowest common denominator.
- X2D, AMS 2 Pro, dual nozzle, HMS, K profiles, and Virtual Printer can evolve independently.
- Vendor protocol changes are isolated behind adapters.
- A common contract-test suite becomes possible.
- The architecture remains compatible with a single Docker container and ARM64/Umbrel deployment.

### Negative

- More explicit domain types and mapping code are required.
- The same physical state may exist as both a vendor-native representation and a normalized FoxForge representation.
- Capability versioning and compatibility rules must be maintained deliberately.
- Frontend/API code must be capability-aware.
- Deciding whether a feature is common or vendor-specific will sometimes require architectural review.

## Migration plan

FoxForge does not yet have a production printer-management core, so this plan is primarily a bootstrap sequence rather than a migration of existing application code.

### Phase 0: Record the architecture

- Keep this ADR as the canonical dependency decision.
- Maintain detailed interface design separately from the ADR.

**Exit criterion:** implementation work references this ADR and does not invent a competing printer boundary ad hoc.

### Phase 1: Define vendor-neutral contracts

Create FoxForge-owned types for:

- printer identity;
- normalized printer and job states;
- `PrinterAdapter`;
- capability descriptors/contracts;
- normalized printer events;
- `AdapterRegistry`;
- adapter errors.

Also create a `FakePrinterAdapter` for tests.

**Exit criterion:** fleet/application tests can run against a fake printer without importing any vendor package.

### Phase 2: Implement Bambu as the reference adapter

Compose Bambu transports and model-specific behavior behind `BambuAdapter`.

Existing FoxForge X2D/BambuTunnelLocal work should become Bambu infrastructure/transport behavior rather than common-core logic.

When copied or derived upstream code is used, preserve required copyright/license notices and document provenance. Newly written FoxForge contracts remain clearly identified as FoxForge code.

**Exit criterion:** common application code does not import `BambuMQTTClient`, Bambu protocol DTOs, or Bambu state classes.

### Phase 3: Introduce `PrinterRegistry` / `FleetService`

These services operate only on `PrinterAdapter`, normalized snapshots, capabilities, and events.

**Exit criterion:** fake and Bambu adapters can coexist in the same fleet service.

### Phase 4: Route queue dispatch through `PrintExecutionCapability`

Queue logic must not perform FTP uploads, MQTT commands, or Moonraker requests directly.

**Exit criterion:** queue integration tests depend only on common capability contracts.

### Phase 5: Implement MoonrakerAdapter

Use Moonraker/Klipper as the first architecture-validation adapter. Ender-3 V3 KE/OpenKE is an appropriate real validation target.

Moonraker code must not import Bambu state/domain types.

**Exit criterion:** one Bambu printer and one Moonraker printer can participate in a common queue/fleet without vendor branches in application services.

### Phase 6: Add common material-system integration

Normalize material units, slots, loaded spools, active sources, and slot-change events. Keep AMS-only functions in Bambu extensions.

**Exit criterion:** spool inventory does not depend on an `AMSState` or other Bambu-specific object.

### Phase 7: Capability-driven API and UI

Expose normalized capabilities to clients and render controls conditionally. Vendor panels may expose extension capabilities without changing the common model.

**Exit criterion:** Bambu and Moonraker screens can differ substantially while sharing fleet, queue, and inventory workflows.

### Phase 8: Enforce architecture in CI

Add dependency tests that reject imports such as:

```text
core/application -> adapters.bambu
core/application -> adapters.moonraker
queue             -> bambu transport
inventory         -> bambu AMS state
```

while allowing:

```text
adapters.bambu     -> printer contracts
adapters.moonraker -> printer contracts
application        -> printer contracts
```

## Acceptance criteria

The decision is considered successfully implemented when all of the following are true:

1. Common/domain/application packages do not import vendor transport clients, vendor protocol DTOs, or vendor state classes.
2. A shared contract-test suite runs against `FakePrinterAdapter`, `BambuAdapter`, and `MoonrakerAdapter`.
3. The contract tests cover connect, disconnect, snapshot, capability discovery, event delivery, reconnect, and error normalization.
4. A mixed-farm integration test can operate at least one Bambu and one Moonraker printer through common fleet/queue services without vendor checks in those services.
5. Bambu extensions retain AMS/AMS 2 Pro, drying, HMS, K profiles, dual-nozzle, Virtual Printer, and X2D-specific functionality without adding those concepts to the base snapshot.
6. Moonraker adapter code does not import Bambu state or Bambu domain classes.
7. Adding a third adapter that only uses existing capabilities requires a new adapter package, registration, and tests, but no changes to `FleetService`, `QueueService`, inventory core, or the base printer snapshot.
8. Event/reconnect tests cover duplicate delivery, late events, adapter restart, printer restart, and job-completion replay so queue and spool accounting consumers can remain idempotent.
9. The adapter architecture does not require separate per-vendor daemons or containers and remains compatible with amd64/arm64 Docker and Umbrel-friendly deployment.
