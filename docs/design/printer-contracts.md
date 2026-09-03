# Printer contracts v1

- **Status:** Design specification
- **Related ADR:** [ADR 0001: PrinterAdapter architecture](../adr/0001-printer-adapter-architecture.md)
- **Date:** 2026-09-03
- **Scope:** `PrinterAdapter`, `PrintExecutionCapability`, `MaterialSystemCapability`, and the minimum supporting common types required to make those contracts precise.

This document is normative design guidance for the first FoxForge printer integration layer. It does **not** implement the interfaces.

The examples use Python-shaped asynchronous pseudocode because the upstream printer-management projects studied by FoxForge are Python/FastAPI based. The semantics, not Python syntax, are the contract.

Normative words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used intentionally.

## 1. Design goals

The v1 contracts must satisfy all of the following:

1. Fleet, queue, and inventory code can operate without importing vendor packages.
2. Bambu-specific state is not part of the common snapshot.
3. Moonraker does not emulate AMS, HMS, K profiles, or other Bambu concepts.
4. A Bambu adapter can still expose richer extension capabilities alongside the common contracts.
5. Queue dispatch can be made idempotent and recoverable.
6. Material inventory can identify physical printer slots without depending on AMS terminology.
7. Event consumers can tolerate reconnects and duplicate delivery.
8. The contracts remain practical for an in-process, single-container Docker/ARM64/Umbrel deployment.

## 2. Package/dependency target

The intended dependency shape is:

```text
foxforge.domain.printers
    <- foxforge.application.fleet
    <- foxforge.application.queue
    <- foxforge.application.inventory

foxforge.domain.printers
    <- foxforge.adapters.bambu
    <- foxforge.adapters.moonraker
```

The domain package MUST NOT import either adapter package.

A possible future package layout is illustrative only:

```text
foxforge/
  domain/
    printers/
      adapter.py
      models.py
      events.py
      errors.py
      capabilities/
        print_execution.py
        material_system.py
  adapters/
    bambu/
    moonraker/
```

## 3. Common identifiers and scalar rules

### 3.1 `PrinterId`

`PrinterId` is the stable FoxForge database identity of a configured printer.

```text
PrinterId = UUID/string opaque to adapters
```

Adapters MUST treat the value as opaque and MUST NOT derive vendor behavior from it.

### 3.2 Opaque vendor identifiers

Identifiers such as `VendorJobId`, `MaterialUnitId`, and `MaterialSlotId` are strings whose internal format is owned by the adapter.

Common code MUST compare and persist them but MUST NOT parse them.

For example, a Bambu adapter is free to produce a slot id such as `ams:0:slot:2`, but common code must treat the complete string as an opaque key.

### 3.3 Time

All timestamps crossing the common contract use timezone-aware UTC instants.

### 3.4 Fractions

Progress and remaining estimates use normalized fractions from `0.0` through `1.0` where applicable. Unknown values are `None`; sentinel values such as `-1` are forbidden in the common domain.

## 4. Common enums

```python
class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"


class OperationalState(Enum):
    OFFLINE = "offline"
    IDLE = "idle"
    PREPARING = "preparing"
    PRINTING = "printing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLING = "cancelling"
    UNKNOWN = "unknown"


class JobState(Enum):
    QUEUED = "queued"
    TRANSFERRING = "transferring"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    PRINTING = "printing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"
```

`OperationalState` describes the printer resource. `JobState` describes one observed or submitted print job. They MUST NOT be assumed to have a one-to-one mapping.

## 5. `PrinterIdentity`

Identity is available before connection and remains stable for the lifetime of the configured adapter.

```python
@dataclass(frozen=True)
class PrinterIdentity:
    printer_id: PrinterId
    display_name: str
    vendor: str
    model: str | None
    serial_number: str | None
    adapter_kind: str
```

Rules:

- `vendor` is human/domain metadata such as `"bambu_lab"` or `"creality"`; it is not used for adapter dispatch.
- `adapter_kind` is the configured infrastructure kind such as `"bambu"` or `"moonraker"` and is interpreted only by the composition root/adapter registry.
- `serial_number` MAY be unavailable for protocols that do not expose one.
- Connection-time discovery MAY refine `model` or `serial_number`, but `printer_id` MUST remain stable.

## 6. `PrinterSnapshot`

The base snapshot intentionally contains only state that is meaningful for essentially every printer workflow.

```python
@dataclass(frozen=True)
class PrinterSnapshot:
    printer_id: PrinterId
    connection: ConnectionState
    operational_state: OperationalState
    active_job: ActiveJobSnapshot | None
    observed_at: datetime
    stale: bool
    fault_summary: tuple[PrinterFaultSummary, ...] = ()
```

```python
@dataclass(frozen=True)
class ActiveJobSnapshot:
    vendor_job_id: str | None
    name: str | None
    state: JobState
    progress: float | None
    elapsed_seconds: int | None
    remaining_seconds: int | None
    current_layer: int | None
    total_layers: int | None
```

```python
@dataclass(frozen=True)
class PrinterFaultSummary:
    code: str
    severity: Literal["info", "warning", "error", "critical"]
    message: str | None
```

Rules:

- `fault_summary` is generic and intentionally shallow. Detailed HMS, Klipper shutdown traces, or vendor diagnostics belong to extension capabilities.
- `stale=True` means the adapter is returning its last known state because freshness guarantees were lost.
- An offline printer SHOULD return its last known job information only when clearly marked stale; otherwise `active_job=None`.
- The snapshot MUST NOT contain raw MQTT JSON, Moonraker JSON, AMS objects, K profiles, HMS DTOs, or vendor-only fields.

## 7. Capability model

Capabilities are typed runtime objects returned by the adapter.

A stable descriptor accompanies each capability:

```python
@dataclass(frozen=True)
class CapabilityDescriptor:
    capability_id: str
    major_version: int
```

Initial common ids:

```text
foxforge.print_execution / v1
foxforge.material_system / v1
```

A capability id plus major version defines compatibility. Backward-compatible additions MAY occur within a major version; breaking semantic changes require a new major version.

Typed resolution is preferred over a generic string-command API:

```python
C = TypeVar("C")

class CapabilityResolver(Protocol):
    def capability(self, capability_type: type[C]) -> C | None: ...
```

Rules:

- Unsupported capabilities return `None`; callers MUST NOT probe support by invoking a method and waiting for `NotImplementedError`.
- Vendor extension capability types MAY participate in the same resolver.
- Capability availability MAY change after connection because model, firmware, or attached hardware was discovered. Such a change MUST emit `CapabilityChanged`.

## 8. Printer events

Each adapter exposes a fan-out event stream. Every subscription is independent; it is not a work queue where one subscriber consumes events on behalf of another.

```python
@dataclass(frozen=True)
class PrinterEvent:
    event_id: UUID
    printer_id: PrinterId
    connection_epoch: UUID
    sequence: int
    observed_at: datetime
    emitted_at: datetime
    kind: PrinterEventKind
    payload: object
```

Initial common event kinds:

```text
connection_changed
printer_state_changed
job_state_changed
job_progress_changed
capability_changed
material_system_changed
snapshot_reconciled
```

Delivery rules:

1. Delivery is **at least once**. Consumers MUST be safe against duplicate `event_id` values.
2. `sequence` is monotonic only within one `connection_epoch`.
3. A new successful connection/reconnection creates a new `connection_epoch`; consumers MUST NOT compare sequence values across epochs.
4. The adapter MUST preserve event ordering within one epoch for events it emits.
5. After reconnect, the adapter MUST emit or make available a reconciled current snapshot so consumers are not forced to reconstruct state solely from missed events.
6. Common application logic SHOULD react to state transitions but MUST reconcile against snapshots for durable workflows such as queue dispatch and spool accounting.

## 9. Error contract

All common capability operations fail through normalized adapter errors.

```python
class PrinterErrorCode(Enum):
    CONNECTION_UNAVAILABLE = "connection_unavailable"
    AUTHENTICATION_FAILED = "authentication_failed"
    TIMEOUT = "timeout"
    BUSY = "busy"
    NOT_READY = "not_ready"
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED = "unsupported"
    CONFLICT = "conflict"
    REMOTE_REJECTED = "remote_rejected"
    INDETERMINATE = "indeterminate"
    INTERNAL_ADAPTER_ERROR = "internal_adapter_error"
```

```python
@dataclass
class PrinterAdapterError(Exception):
    code: PrinterErrorCode
    message: str
    retryable: bool
    vendor_code: str | None = None
```

Rules:

- Vendor exception classes MUST NOT escape into common application code.
- `INDETERMINATE` is used when a side effect may have occurred but the adapter cannot prove whether it succeeded. Queue code MUST reconcile printer state before retrying such an operation.
- `vendor_code` is optional diagnostic metadata and MUST NOT be used as a branch key in common workflows.

# 10. Exact `PrinterAdapter` v1 contract

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

## 10.1 `identity`

- MUST be callable before connection.
- MUST NOT perform network I/O.
- `printer_id` MUST remain stable.

## 10.2 `connect()`

- MUST be idempotent.
- A call while already connected MUST NOT create duplicate transport sessions.
- Success means the adapter has enough current information to publish a valid initial `PrinterSnapshot`.
- Authentication or connection failures raise normalized `PrinterAdapterError`.
- Reconnect loops MAY be implemented internally after the first successful connection.

## 10.3 `disconnect()`

- MUST be idempotent.
- MUST stop adapter-owned reconnect loops and transport sessions.
- MUST leave `snapshot().connection == DISCONNECTED` after completion.
- MUST NOT delete persisted FoxForge printer configuration.

## 10.4 `snapshot()`

- MUST return immediately from adapter-owned normalized state and MUST NOT perform network I/O.
- MUST be safe to call before the first successful connection; in that case it returns an `OFFLINE`/disconnected snapshot.
- Freshness is expressed by `observed_at` and `stale`, not by hidden blocking refresh behavior.
- Transport polling or refresh cadence belongs inside the adapter implementation.

This decision intentionally prevents application code from causing accidental vendor-specific polling patterns.

## 10.5 `capability()`

- MUST return the same logical capability object for the same adapter while that capability remains available.
- MUST return `None` when unsupported.
- MUST NOT fabricate a compatibility shim that exposes operations with false semantics merely to make a capability appear present.

## 10.6 `events()`

- Each invocation MUST create an independent subscription.
- Slow subscribers MUST NOT be allowed to block vendor transport processing indefinitely.
- Overflow policy must be observable: if an implementation drops intermediate progress events, it MUST still reconcile the latest state and MUST NOT silently drop terminal job-state transitions.

# 11. `PrintExecutionCapability` v1

`PrintExecutionCapability` is the only common capability required for a printer to be eligible for automated queue dispatch.

It represents the semantic operation:

> take a FoxForge-managed printable artifact, apply a common target/material selection, deliver it through the vendor's required transport(s), and request the printer to start it.

The queue MUST NOT know whether this required Bambu FTP + MQTT, Moonraker upload + HTTP/WebSocket, or another protocol.

## 11.1 Descriptor

```python
class PrintArtifactFormat(Enum):
    GCODE = "gcode"
    THREE_MF = "3mf"


@dataclass(frozen=True)
class PrintExecutionDescriptor(CapabilityDescriptor):
    accepted_formats: frozenset[PrintArtifactFormat]
    supports_plate_selection: bool
    supports_material_bindings: bool
```

For v1:

```text
capability_id = "foxforge.print_execution"
major_version = 1
```

## 11.2 Local artifact contract

FoxForge v1 is an in-process/self-hosted architecture, so queue dispatch uses a read-only local artifact reference.

```python
@dataclass(frozen=True)
class LocalPrintArtifact:
    artifact_id: str
    path: Path
    filename: str
    format: PrintArtifactFormat
    size_bytes: int
    sha256: str
```

Rules:

- `path` MUST be absolute and point to an application-managed readable file for the duration of the call.
- The adapter MUST NOT modify, rename, or delete the source file.
- `sha256` is the identity/fingerprint used for idempotency and diagnostics.
- A future out-of-process adapter protocol may replace `path` with a stream/object reference without changing the higher-level print semantics; that change requires a separate transport-level design.

## 11.3 Artifact selection

```python
@dataclass(frozen=True)
class PrintArtifactSelection:
    plate_index: int | None = None
```

Rules:

- `plate_index` is zero-based in the FoxForge contract.
- It is meaningful only for artifact formats that can contain multiple printable plates.
- If `plate_index` is supplied and the descriptor says `supports_plate_selection=False`, assessment MUST report `UNSUPPORTED_SELECTION` and submit MUST reject the request.

## 11.4 Material bindings

A print artifact may contain one or more logical material inputs. Queue/inventory code binds those inputs to opaque physical printer slots.

```python
@dataclass(frozen=True)
class MaterialBinding:
    material_index: int
    slot_id: MaterialSlotId
```

Rules:

- `material_index` is zero-based and refers to the artifact/slicer logical material ordering.
- `slot_id` comes from `MaterialSystemCapability`; common code MUST NOT derive it from AMS numbering or vendor topology.
- A single-spool Moonraker printer can expose one external slot and accept a single binding.
- Vendor-specific mapping details are translated inside the adapter.

## 11.5 Execution request

```python
@dataclass(frozen=True)
class PrintExecutionRequest:
    dispatch_id: UUID
    artifact: LocalPrintArtifact
    selection: PrintArtifactSelection | None = None
    material_bindings: tuple[MaterialBinding, ...] = ()
    requested_name: str | None = None
```

`dispatch_id` is generated and durably persisted by the queue **before** invoking the adapter.

## 11.6 Assessment

Assessment is side-effect free.

```python
class PrintAssessmentBlockerCode(Enum):
    OFFLINE = "offline"
    BUSY = "busy"
    NOT_READY = "not_ready"
    UNSUPPORTED_ARTIFACT = "unsupported_artifact"
    UNSUPPORTED_SELECTION = "unsupported_selection"
    MATERIAL_BINDING_INVALID = "material_binding_invalid"
    MATERIAL_SOURCE_UNAVAILABLE = "material_source_unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PrintAssessmentBlocker:
    code: PrintAssessmentBlockerCode
    message: str | None = None


@dataclass(frozen=True)
class PrintExecutionAssessment:
    eligible: bool
    blockers: tuple[PrintAssessmentBlocker, ...]
    observed_at: datetime
```

Assessment is advisory. Printer state may change after assessment, so successful assessment does not reserve the printer and does not guarantee submit success.

## 11.7 Dispatch receipt

```python
@dataclass(frozen=True)
class PrintDispatchReceipt:
    dispatch_id: UUID
    accepted_at: datetime
    vendor_job_id: str | None
    artifact_sha256: str
```

Returning a receipt means the adapter has sufficient evidence that the vendor accepted the start request. It does **not** mean the printer has already reached `PRINTING`; the queue must observe/reconcile the subsequent job state.

## 11.8 Exact capability protocol

```python
class PrintExecutionCapability(Protocol):
    @property
    def descriptor(self) -> PrintExecutionDescriptor: ...

    async def assess(
        self,
        request: PrintExecutionRequest,
    ) -> PrintExecutionAssessment: ...

    async def submit(
        self,
        request: PrintExecutionRequest,
    ) -> PrintDispatchReceipt: ...
```

## 11.9 `assess()` semantics

- MUST NOT upload, delete, start, pause, stop, or otherwise mutate printer state.
- MUST validate artifact format and request shape.
- SHOULD validate current connection/readiness and known material-slot availability.
- MUST return structured blockers rather than vendor-specific text as the primary machine-readable result.

## 11.10 `submit()` semantics

- MUST treat `dispatch_id` as an idempotency key within the lifetime of the adapter instance.
- Repeating the same `dispatch_id` with the same artifact fingerprint/request MUST return the same logical receipt or reconcile the existing submission instead of intentionally starting a second print.
- Reusing a `dispatch_id` with a different artifact fingerprint or materially different request MUST fail with `CONFLICT`.
- The application/queue owns **durable** idempotency across process restarts by persisting `dispatch_id`, the request fingerprint, and any receipt before retry decisions.
- If the adapter cannot tell whether a start command was accepted after a timeout/connection loss, it MUST raise `INDETERMINATE`; the queue MUST reconcile printer/job state before retrying.
- Vendor-specific defaults MUST remain inside the adapter. The queue MUST NOT need to know FTP paths, MQTT topics, Moonraker API methods, Bambu plate numbering, or similar details.

## 11.11 Out of scope for `PrintExecutionCapability` v1

The following belong to other common or vendor-specific capabilities:

- pause/resume/cancel of an already running job;
- browsing/deleting remote files;
- arbitrary G-code or macros;
- AMS drying;
- calibration;
- K profiles;
- HMS details;
- Bambu Virtual Printer behavior.

# 12. `MaterialSystemCapability` v1

`MaterialSystemCapability` provides a vendor-neutral observation of the physical material sources attached to one printer.

Version 1 is deliberately **observation-first**. Persistent FoxForge spool assignment is application/inventory state, not adapter state, and vendor-specific material-management commands are not forced into this common capability.

This lets the same contract model:

- Bambu AMS / AMS 2 Pro / AMS HT;
- Creality CFS;
- a single external spool on a Moonraker printer;
- multiple external/manual feeds;
- future material systems.

## 12.1 Descriptor

```python
@dataclass(frozen=True)
class MaterialSystemDescriptor(CapabilityDescriptor):
    reports_active_source: bool
    reports_remaining_fraction: bool
    reports_material_identity: bool
    reports_tag_identity: bool
```

For v1:

```text
capability_id = "foxforge.material_system"
major_version = 1
```

These booleans describe available observations; they do not imply a specific sensor technology.

## 12.2 Unit kinds

```python
class MaterialUnitKind(Enum):
    MULTI_SLOT = "multi_slot"
    EXTERNAL = "external"
    TOOLHEAD = "toolhead"
    OTHER = "other"
```

`MULTI_SLOT` means only that the unit contains multiple independently addressable sources. Common code MUST NOT equate it with AMS or CFS.

## 12.3 Slot state

```python
class MaterialPresence(Enum):
    EMPTY = "empty"
    LOADED = "loaded"
    UNKNOWN = "unknown"


class MaterialActivity(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    UNKNOWN = "unknown"
```

## 12.4 Detected material

```python
@dataclass(frozen=True)
class MaterialColor:
    rgba_hex: str


@dataclass(frozen=True)
class MaterialTagIdentity:
    scheme: str
    value: str


@dataclass(frozen=True)
class DetectedMaterial:
    material_family: str | None
    vendor_name: str | None
    product_name: str | None
    color: MaterialColor | None
    tag: MaterialTagIdentity | None
    remaining_fraction: float | None
```

Rules:

- `material_family` is a normalized human/domain value such as `PLA`, `PETG`, `ABS`, or `TPU` when known. Unknown/custom types remain strings rather than being discarded.
- `tag.scheme` is descriptive metadata such as a vendor RFID/NFC namespace. Inventory code may use it for matching, but common material workflows MUST NOT assume every slot has a tag.
- Tag secrets or authentication material MUST NOT be exposed through this type.
- `remaining_fraction` is an observed/estimated fraction from `0.0` to `1.0`; it is `None` if the printer cannot report a meaningful estimate.
- FoxForge `spool_id` is intentionally absent. Physical-slot-to-inventory-spool assignment belongs to the inventory domain.

## 12.5 Material unit and slot

```python
@dataclass(frozen=True)
class MaterialSlotSnapshot:
    slot_id: MaterialSlotId
    unit_id: MaterialUnitId
    position: int
    label: str | None
    presence: MaterialPresence
    activity: MaterialActivity
    detected_material: DetectedMaterial | None


@dataclass(frozen=True)
class MaterialUnitSnapshot:
    unit_id: MaterialUnitId
    kind: MaterialUnitKind
    label: str | None
    position: int
    slots: tuple[MaterialSlotSnapshot, ...]
```

Rules:

- `unit_id` and `slot_id` MUST be stable for a given detected topology across normal reconnects/restarts.
- If the physical topology genuinely changes, the adapter MAY publish new ids and MUST emit `material_system_changed`.
- `position` is a presentation/sorting hint only. Common code MUST use ids, not positions, as durable keys.
- Vendor metadata such as AMS humidity, dryer temperature, feeder sub-state, motor state, or CFS-specific diagnostics is not added to these common snapshots unless later promoted through a separate ADR/version.

## 12.6 Snapshot

```python
@dataclass(frozen=True)
class MaterialSystemSnapshot:
    printer_id: PrinterId
    units: tuple[MaterialUnitSnapshot, ...]
    observed_at: datetime
    stale: bool
```

A printer with one manual external spool can legitimately return:

```text
1 EXTERNAL unit
  -> 1 slot
```

This allows queue/inventory material binding without fabricating a multi-material system.

## 12.7 Exact capability protocol

```python
class MaterialSystemCapability(Protocol):
    @property
    def descriptor(self) -> MaterialSystemDescriptor: ...

    def snapshot(self) -> MaterialSystemSnapshot: ...
```

Version 1 intentionally has no mutation methods.

The method:

- MUST return immediately from normalized adapter-owned state;
- MUST NOT perform network I/O;
- MUST report stale data explicitly;
- MUST use the same opaque `slot_id` values accepted by `PrintExecutionRequest.material_bindings`.

Updates arrive through the parent `PrinterAdapter.events()` stream as `material_system_changed` events. Event payload SHOULD include the new `MaterialSystemSnapshot` or enough information for consumers to immediately read the updated snapshot.

## 12.8 Why spool assignment is not an adapter method

FoxForge inventory may persist:

```text
(printer_id, slot_id) -> spool_id
```

That relationship belongs to FoxForge, even if the printer reports RFID/tag metadata that helps create or verify the association.

Therefore v1 does **not** define:

```text
MaterialSystemCapability.assign_spool(spool_id)
```

An adapter does not own FoxForge inventory identity.

If a vendor can write material metadata back to the printer, that operation belongs initially in a vendor extension. It can be promoted to a common capability later if multiple vendors expose compatible semantics.

# 13. Interaction between the three contracts

Typical queue flow:

```text
PrinterAdapter
  -> snapshot() says IDLE/CONNECTED
  -> capability(MaterialSystemCapability)
       -> material snapshot exposes slot ids
  -> queue resolves FoxForge spool assignments
  -> capability(PrintExecutionCapability)
       -> assess(request with MaterialBinding[])
       -> submit(request)
  -> PrinterAdapter events()
       -> job_state_changed PREPARING/PRINTING/COMPLETED
```

The queue never imports a Bambu or Moonraker class.

Typical Bambu-specific UI flow can coexist:

```text
PrinterAdapter
  -> common PrinterSnapshot
  -> common MaterialSystemCapability
  -> BambuDryingCapability
  -> BambuHmsCapability
  -> BambuDualNozzleCapability
```

A Moonraker UI may instead resolve Moonraker/Klipper extensions without changing any of the common types above.

# 14. Required contract tests

The same adapter contract suite MUST run against at least `FakePrinterAdapter`, `BambuAdapter`, and `MoonrakerAdapter` once those implementations exist.

## 14.1 `PrinterAdapter` tests

1. Identity is available before connect.
2. `connect()` is idempotent.
3. `disconnect()` is idempotent.
4. `snapshot()` performs no external network call.
5. Pre-connect snapshot is valid and offline/disconnected.
6. Vendor exceptions are normalized.
7. Independent event subscribers each receive terminal state events.
8. Duplicate/replayed events preserve `event_id` for consumer dedupe when they represent the same logical event.
9. Sequence numbers are monotonic within a connection epoch.
10. Reconnect creates a new epoch and produces reconciliation state.
11. Capability availability changes produce `capability_changed`.

## 14.2 `PrintExecutionCapability` tests

1. `assess()` has no side effects.
2. Unsupported artifact formats are blocked deterministically.
3. Unsupported plate selection is blocked deterministically.
4. Invalid material slot ids are rejected without vendor-type leakage.
5. The same `dispatch_id` plus same fingerprint does not intentionally trigger a second start.
6. The same `dispatch_id` plus a different fingerprint returns `CONFLICT`.
7. A known remote rejection returns normalized `REMOTE_REJECTED` or a more specific normalized error.
8. Ambiguous timeout after a possible start returns `INDETERMINATE`.
9. Successful `submit()` returns a receipt before the queue relies on subsequent normalized job events.
10. The test double can simulate transfer/start delay without forcing queue code to know transport details.

## 14.3 `MaterialSystemCapability` tests

1. Snapshot contains opaque stable unit/slot ids.
2. Positions may change without application code treating them as identity.
3. A single external-spool printer is representable without fake AMS fields.
4. Empty, loaded, and unknown slots are distinct states.
5. Missing RFID/tag data is valid.
6. Missing remaining estimate is valid.
7. Material update emits `material_system_changed` and updates the cached snapshot.
8. Reconnect preserves slot ids when physical topology has not changed.
9. Moonraker implementation imports no Bambu state/domain types.
10. Bambu-specific AMS/dryer/HMS data does not appear in the common material snapshot.

# 15. Architecture enforcement tests

CI SHOULD add import-boundary tests once implementation begins.

Forbidden examples:

```text
application.queue     -> adapters.bambu
application.inventory -> adapters.bambu
application.fleet     -> adapters.moonraker
domain.printers       -> adapters.*
```

Allowed examples:

```text
application.*         -> domain.printers
adapters.bambu        -> domain.printers
adapters.moonraker    -> domain.printers
composition_root      -> adapters.*
```

# 16. Decisions intentionally deferred

Separate design/ADR work is required before defining the following:

- common pause/resume/cancel (`JobControlCapability`);
- common remote file browsing/storage;
- camera stream abstraction;
- thermal/heater/fan controls;
- arbitrary G-code/macros;
- Bambu extension capability boundaries;
- common dryer semantics, if they prove cross-vendor;
- out-of-process adapters/plugins;
- capability negotiation over a public plugin API;
- persistence schema for adapter configuration and secrets.

Deferring these prevents the initial contracts from becoming Bambu-shaped before the Bambu and Moonraker implementations have validated the boundary.

# 17. Implementation entry criteria

Implementation of Phase 1 from ADR 0001 may begin when maintainers accept these three v1 contracts as the baseline.

The first implementation PR should contain only:

1. common types/contracts/errors/events;
2. `FakePrinterAdapter`;
3. contract tests;
4. no real Bambu or Moonraker transport code yet.

The next PR should implement Bambu against those contracts, followed by Moonraker as the architecture-validation adapter.
