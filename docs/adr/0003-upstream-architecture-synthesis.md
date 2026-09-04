# ADR 0003: Upstream architecture synthesis

- **Status:** Accepted
- **Date:** 2026-09-04
- **Decision owners:** FoxForge maintainers
- **Scope:** How Bambuddy, PrintBuddy and PrintOps inform FoxForge architecture and implementation choices
- **Builds on:** [ADR 0001: PrinterAdapter architecture](0001-printer-adapter-architecture.md)

## Context

FoxForge is not intended to become a renamed fork of Bambuddy, PrintBuddy or PrintOps. It is a separate self-hosted 3D-printer management platform whose core requirements are:

- multi-vendor printer management;
- deep Bambu Lab support rather than a lowest-common-denominator abstraction;
- Moonraker/Klipper support;
- independent filament/spool inventory;
- AMS/CFS/external-spool integration;
- durable print queue and farm-management workflows;
- Docker, ARM64 and Umbrel-friendly deployment;
- clear provenance when upstream code or material is copied or derived.

ADR 0001 already defines the core printer boundary: FoxForge owns a small vendor-neutral `PrinterAdapter`, normalized common domain types and typed capabilities, while vendor transports and vendor-only semantics remain behind adapters.

This ADR records the broader architectural synthesis from the three upstream projects so later implementation work does not repeatedly re-litigate which ideas FoxForge should adopt.

The upstream snapshots reviewed for this decision were:

| Project | Repository | Reviewed commit |
| --- | --- | --- |
| Bambuddy | `maziggy/bambuddy` | `2d16ed9ad01ec705d7e746d2ee48797ac20218c1` |
| PrintBuddy | `vmhomelab/printbuddy` | `b9f81c7a9a5fae861daf2e91737e4e978db8aa5e` |
| PrintOps | `ichwars/PrintOps` | `dd3be37630cfb1c7b30d27c4bd68bba4cb3a9da3` |

The repositories may evolve after these commits. Future upstream research should record the exact commit reviewed and update this ADR only when the architectural conclusion changes.

## Decision

FoxForge will use the three upstream projects as **specialized reference implementations**, not as a single inherited application architecture.

The durable rule is:

> **Bambuddy supplies Bambu depth, PrintBuddy supplies multi-vendor provider ideas, PrintOps supplies operations/farm ideas, and FoxForge keeps its own domain, capability, event, queue, inventory and deployment architecture.**

No upstream project is the framework on which FoxForge is built.

### 1. Bambuddy is the Bambu reference implementation

Bambuddy is the preferred upstream source for understanding Bambu-specific behavior, including areas such as:

- MQTT command/state semantics;
- connection and reconnect behavior;
- LAN authentication and device-specific state handling;
- project/file delivery behavior;
- AMS/AMS-family tray semantics;
- HMS and error interpretation;
- Bambu job lifecycle mapping;
- model- and firmware-specific behavior;
- Bambu-oriented product/UX expectations.

FoxForge may reuse ideas or, where appropriate and license-compatible, derive implementation details from Bambuddy, but Bambu protocol concepts must terminate inside the Bambu adapter/infrastructure boundary.

Bambuddy is **not** the template for FoxForge's common printer domain, queue, inventory or scheduler.

### 2. PrintBuddy is the multi-vendor integration reference

PrintBuddy is the preferred upstream source for ideas around provider registration, printer-family isolation and operating multiple vendor families from one application.

FoxForge adopts the principle of isolating printer families behind factories/providers/adapters, but does **not** adopt a Bambu-shaped provider protocol as the common printer contract.

FoxForge's common contract remains the smaller `PrinterAdapter` plus typed capabilities from ADR 0001.

A third vendor that only uses existing capabilities should be addable through a new adapter package, registration and tests without modifying queue, inventory or fleet core logic.

### 3. PrintOps is the operations and farm-management reference

PrintOps is the preferred upstream source for product and domain ideas above the printer-driver layer, especially:

- projects and production workflows;
- print operations and scheduling;
- queue/farm dashboards;
- operational history;
- warehouse/inventory workflows;
- costing and production-oriented domain separation.

FoxForge should reuse these ideas at the application/domain level while keeping scheduler, queue and inventory code independent of Bambu/Moonraker transports.

A scheduler must answer questions such as "which printers can satisfy this job?" through FoxForge capabilities and persisted application state. It must not know how MQTT, FTPS, Moonraker HTTP or vendor-native status payloads work.

### 4. FoxForge keeps its current architecture as the integration skeleton

The current FoxForge architecture remains canonical:

```text
Web UI
  |
REST / realtime API
  |
Application services
  |-- Fleet
  |-- Queue
  |-- Inventory
  `-- Scheduler
  |
FoxForge domain
  |
PrinterAdapter + typed capabilities
  |-------------------|
BambuAdapter       MoonrakerAdapter
  |                    |
MQTT / storage     HTTP / WebSocket
```

This means:

- FoxForge common/domain/application code owns common semantics;
- vendor packages own protocol parsing and vendor mapping;
- queue owns durable dispatch safety;
- inventory owns FoxForge spool identity and mass history;
- scheduler/farm code depends on application capabilities, not transports;
- API DTOs and frontend models consume FoxForge contracts rather than upstream/vendor DTOs.

### 5. Do not create a lowest-common-denominator `GenericPrinter`

FoxForge must not collapse every printer into a large optional interface such as:

```text
pause
resume
stop
ams?
drying?
hms?
k_profile?
macros?
bed_mesh?
...
```

Instead, the base adapter remains small and features are discovered through typed capabilities.

Common examples may include:

- print execution;
- job control;
- material system;
- camera;
- file/project storage;
- thermal state.

Vendor-specific examples may include:

- Bambu AMS operations/drying;
- Bambu HMS;
- Bambu K profiles;
- Bambu dual-nozzle behavior;
- Bambu Virtual Printer/X2D-specific storage;
- Moonraker macros;
- Moonraker/Klipper object or bed-mesh extensions.

A feature is promoted into a common capability only when its semantics are genuinely vendor-independent and a FoxForge workflow benefits from that common meaning.

### 6. Inventory remains a separate bounded context

FoxForge spool identity is not a property of a printer protocol object.

The inventory model owns concepts such as:

```text
Material
Spool
Location
Assignment
Reservation
Consumption
Correction
```

A printer material system exposes physical source/slot state and opaque slot IDs. The inventory domain associates FoxForge spools with those physical locations.

An AMS, CFS or external holder is therefore a material location/system, not the owner of the spool's business identity or accounting history.

This allows one physical spool to move between printers and retain one durable FoxForge history.

### 7. Queue safety stays FoxForge-owned

FoxForge's existing durable queue semantics take precedence over upstream queue implementations.

In particular:

- dispatch intent is persisted before external side effects;
- ambiguous print starts become `INDETERMINATE`;
- `INDETERMINATE` jobs are not automatically retried;
- receipt-bearing jobs are never blindly redispatched;
- retries are limited to explicitly safe pre-start failures.

PrintOps scheduling ideas may be layered above this queue. They must not weaken these invariants.

### 8. Backend evolution should be event-driven

Printer adapters already expose normalized events as part of ADR 0001. New workflows should increasingly compose around those events rather than vendor polling loops in feature code.

Expected application-level events include concepts such as:

```text
ConnectionChanged
PrinterStateChanged
PrintStarted
JobProgressChanged
PrintCompleted
PrintFailed
MaterialSlotsChanged
SpoolAssignmentChanged
SpoolConsumed
```

Vendor-specific events may exist in namespaced extensions.

Queue, inventory, realtime API and later farm automation must process relevant events idempotently because reconnect/replay/duplicate delivery are normal distributed-system conditions.

### 9. Frontend is capability-driven and FoxForge-owned

The frontend may borrow interaction ideas from all three upstream projects, especially Bambu-oriented detail from Bambuddy and farm/operations workflows from PrintOps, but its architecture remains newly written FoxForge code.

Shared screens should render common FoxForge read models. Deep vendor controls should appear only when the backend exposes the corresponding typed capability.

The frontend must not spread checks such as:

```text
if vendor == "bambu"
```

through generic feature code merely to reach vendor-specific behavior. Vendor extensions should be isolated behind capability-aware feature boundaries.

### 10. Deployment stays single-runtime and vendor-independent

FoxForge will continue to prefer an in-process modular architecture and one deployable application runtime while the project remains suitable for self-hosted Docker, ARM64 and Umbrel targets.

Separate per-vendor daemons or services are not required now. Future out-of-process adapters are allowed only if there is a concrete scaling or isolation need and the current adapter contracts can remain stable across that boundary.

Docker and Umbrel must package the same FoxForge application behavior.

### 11. Upstream adoption must record provenance

Every upstream-inspired change should be classified as one of:

- **Inspired:** design/behavioral idea was studied, implementation is newly written FoxForge code;
- **Derived:** implementation is adapted from upstream code or a substantial upstream implementation pattern;
- **Copied:** upstream code is copied with only limited modification.

For derived/copied material, the PR must preserve all required copyright/license notices and record at minimum:

- upstream repository;
- upstream commit/tag;
- source path(s);
- FoxForge destination path(s);
- upstream license;
- classification (`derived` or `copied`);
- any meaningful modifications.

FoxForge is `AGPL-3.0-only`, but that does not remove the need to preserve upstream notices and compatible third-party license terms.

### 12. Development-source map

Unless a later ADR changes the decision, new design work should use this map:

| FoxForge subsystem | Primary reference | FoxForge rule |
| --- | --- | --- |
| `PrinterAdapter` / capability architecture | FoxForge + PrintBuddy ideas | FoxForge-owned contracts; no Bambu-shaped base interface |
| Bambu MQTT/LAN/state mapping | Bambuddy | Keep protocol/native state inside Bambu adapter |
| Bambu project/file delivery | Bambuddy + validated device behavior | Behind Bambu storage/transport seams |
| AMS/AMS-family semantics | Bambuddy | Common slot/source state only; rich AMS behavior stays Bambu-specific |
| HMS / K profiles / dual nozzle / Bambu extensions | Bambuddy | Typed Bambu capabilities |
| Moonraker/Klipper adapter | Moonraker API + PrintBuddy ideas | No imports from Bambu packages |
| Fleet/provider registry | FoxForge + PrintBuddy | Registry/factory only in infrastructure/composition root |
| Durable queue | FoxForge | Preserve idempotency and `INDETERMINATE` semantics |
| Farm scheduling / production operations | PrintOps | Layer above queue/fleet capabilities; no transport knowledge |
| Inventory / spool accounting | FoxForge + PrintOps/PrintBuddy product ideas | Independent bounded context with FoxForge spool identity |
| Bambu-facing UI patterns | Bambuddy | Product inspiration, not copied frontend architecture |
| Farm/operations UI patterns | PrintOps | Product inspiration behind FoxForge API contracts |
| Frontend architecture | FoxForge | React/TypeScript capability-driven feature structure |
| Docker/ARM64/Umbrel | FoxForge | One application behavior across deployment targets |

Detailed implementation guidance lives in [Upstream adoption map](../design/upstream-adoption-map.md).

## Alternatives

### Alternative A: Fork Bambuddy as FoxForge's base

**Rejected.** Bambu depth is valuable, but a Bambu-native core would force future vendors to enter an architecture shaped around Bambu protocol and state concepts.

### Alternative B: Fork PrintBuddy as the common platform

**Rejected.** Its multi-vendor direction is useful, but FoxForge already has a smaller capability-based adapter boundary and should not replace it with a provider surface derived from one existing client shape.

### Alternative C: Fork PrintOps as the whole product

**Rejected.** Its operational/product domains are useful references, but FoxForge needs a stronger vendor-neutral printer boundary and already has queue/inventory safety semantics that should remain its own.

### Alternative D: Merge codebases wholesale

**Rejected.** Combining three mature codebases would create overlapping domains, incompatible abstractions, high provenance burden, more deployment complexity and difficult long-term upgrades.

### Alternative E: Ignore upstream implementations entirely

**Rejected.** Bambuddy contains valuable Bambu-specific knowledge; PrintBuddy demonstrates multi-vendor integration concerns; PrintOps demonstrates operations/farm workflows. Re-learning all of this independently would be wasteful and increase implementation risk.

## Consequences

### Positive

- FoxForge can remain genuinely multi-vendor while retaining deep Bambu features.
- Upstream research has a durable, explicit purpose instead of influencing code informally through chat.
- Vendor protocol knowledge stays isolated from queue, inventory, scheduler and API contracts.
- Existing FoxForge queue/idempotency safety is preserved.
- Farm-management work can use PrintOps ideas without inheriting its printer-driver coupling.
- Frontend work can be richer per vendor without polluting shared API models.
- Provenance expectations are explicit before significant upstream-derived code enters the repository.
- Future contributors and coding agents have a stable decision map.

### Negative

- FoxForge must maintain more explicit mapping and capability code than a simple fork would require.
- Upstream changes cannot be merged mechanically; they require architectural translation.
- Some useful upstream feature code may need to be reimplemented to preserve boundaries.
- The team must distinguish product inspiration from derived code and document provenance carefully.
- Capability design and event contracts require ongoing architectural review.

## Migration plan

This decision mostly constrains future work because the current FoxForge architecture already aligns with it.

### Phase 1: Make the decision discoverable

- Add this ADR to the documentation index.
- Add a practical upstream-adoption map.
- Add repository-level contributor/agent instructions pointing to the accepted ADRs.

**Exit criterion:** implementation work can discover the decision from the repository without relying on chat memory.

### Phase 2: Enforce package boundaries

- Keep vendor imports out of common domain/application packages.
- Add or extend architecture/import tests when new modules make boundaries easier to violate.
- Keep vendor-specific frontend work behind explicit feature/capability seams.

**Exit criterion:** a vendor-specific feature PR fails CI if it leaks protocol/native vendor types into common code.

### Phase 3: Formalize upstream provenance records

- Record upstream commit/path/license when code is derived or copied.
- Prefer small, reviewable derivations rather than importing entire modules when a narrow behavior is needed.

**Exit criterion:** every derived/copied upstream implementation can be traced from FoxForge back to its source revision.

### Phase 4: Apply the map to roadmap work

- Deep Bambu expansion uses Bambuddy primarily as protocol/behavior reference.
- New vendor support follows the FoxForge/PrintBuddy-style adapter boundary.
- Farm scheduling and production workflow work studies PrintOps primarily at the operations layer.
- Inventory evolution remains FoxForge-owned and independent of printer protocol state.

**Exit criterion:** new roadmap designs state which upstream reference, if any, informed the change and why the resulting FoxForge contract remains independent.

## Acceptance criteria

This ADR is considered successfully applied when:

1. No common application/domain package imports Bambu, Moonraker or another vendor transport/protocol type.
2. No scheduler or queue policy depends directly on MQTT, FTPS, Moonraker HTTP/WebSocket or vendor-native status payloads.
3. Bambu-only behavior can be added without expanding the base `PrinterAdapter` unless the promotion-to-common rule is satisfied.
4. A new vendor using existing capabilities can be registered without changes to fleet, queue or inventory core logic.
5. Inventory retains FoxForge-owned spool identity and does not place `spool_id` inside vendor material snapshots.
6. Existing queue `INDETERMINATE`, receipt and retry invariants remain unchanged by scheduler/farm work.
7. Frontend generic features consume FoxForge API/capability models rather than raw vendor payloads or broad vendor-name branching.
8. Event consumers introduced for queue, inventory or realtime delivery are tested for duplicate/replay/idempotent behavior.
9. Derived/copied upstream code includes traceable provenance and required copyright/license notices.
10. Architecture-significant PRs define acceptance criteria and tests and update repository documentation when they change these boundaries.
