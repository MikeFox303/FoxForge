# Upstream adoption map

This document turns [ADR 0003](../adr/0003-upstream-architecture-synthesis.md) into practical implementation guidance.

It is deliberately more operational than the ADR. The ADR records **why** FoxForge uses each upstream project in a particular role; this document records **where** those ideas belong in FoxForge and what must be tested when they are implemented.

## Governing formula

```text
Bambuddy depth
    +
PrintBuddy multi-vendor ideas
    +
PrintOps operations ideas
    +
FoxForge-owned domain/capability/event/queue/inventory architecture
```

The result must remain FoxForge, not a stitched-together fork.

## Current FoxForge boundaries

The current backend already separates the main architectural concerns:

```text
backend/src/foxforge/
├── domain/
├── application/
├── adapters/
├── infrastructure/
├── api/
├── runtime/
└── testing/
```

The current frontend already has application and feature boundaries and should continue moving toward capability-driven feature isolation rather than vendor checks inside generic screens.

The following ownership rules are normative for new work.

## Subsystem decision matrix

| FoxForge area | Best upstream reference | What to adopt | What not to adopt |
| --- | --- | --- | --- |
| Common printer domain | FoxForge | normalized identity/state/events/errors | upstream/vendor DTOs as public core types |
| `PrinterAdapter` | FoxForge + PrintBuddy ideas | provider isolation, registry/factory composition | Bambu-shaped provider protocol |
| Capability model | FoxForge | small typed interfaces, capability discovery | one giant optional printer API |
| Bambu MQTT/LAN | Bambuddy | protocol behavior, state/command semantics, reconnect lessons | direct MQTT dependencies in application services |
| Bambu project delivery | Bambuddy + device validation | upload/delivery behavior behind `BambuProjectStorage` | queue directly speaking FTPS |
| AMS / AMS 2 Pro / AMS HT | Bambuddy | Bambu slot/tray semantics and operations | making AMS itself the common material model |
| HMS / K profile / calibration / dual nozzle | Bambuddy | Bambu-only typed capabilities | forcing non-Bambu adapters to implement fake equivalents |
| Moonraker/Klipper | official Moonraker API + PrintBuddy ideas | provider isolation, HTTP/WS mapping | importing any Bambu model/state classes |
| Fleet registry | PrintBuddy ideas + FoxForge | registry/factory composition | provider-selection branches throughout application code |
| Durable queue | FoxForge | current dispatch/idempotency/reconciliation semantics | replacing safe queue behavior with upstream convenience logic |
| Farm scheduler | PrintOps | scheduling, assignment and operations concepts | transport-aware scheduler code |
| Inventory/spools | FoxForge + operational ideas from PrintOps/PrintBuddy | separate bounded context, warehouse/location workflows | printer protocol objects owning spool identity |
| Automatic material accounting | FoxForge | reservations, estimates, completion/reconciliation events | blind deduction from vendor status without idempotency |
| Generic frontend | FoxForge | normalized API read models and capabilities | raw Bambu/Moonraker payloads |
| Bambu frontend extensions | Bambuddy product inspiration | rich Bambu-specific controls when capabilities exist | copying Bambuddy frontend architecture wholesale |
| Farm/operations frontend | PrintOps product inspiration | dashboards, workflow ideas | bypassing FoxForge application/API contracts |
| Deployment | FoxForge | one runtime for Docker/ARM64/Umbrel | per-vendor application forks |

## Bambu implementation rule

When implementing a new Bambu feature, work in this order:

1. Identify the native Bambu behavior and protocol/state involved.
2. Study Bambuddy and record the exact upstream commit/path if it materially informs implementation.
3. Decide whether the feature is genuinely common or Bambu-specific using ADR 0001's promotion rule.
4. Keep native protocol DTOs and transport code under the Bambu adapter/infrastructure boundary.
5. Expose only the necessary FoxForge capability/read model upward.
6. Add contract/integration tests before enabling frontend controls.
7. Require physical-device validation before documentation calls the feature production-validated.

Typical Bambu package direction:

```text
application/domain
       ^
       |
FoxForge capability contracts
       ^
       |
BambuAdapter
   |       |
 native   native
 MQTT     project storage
```

Forbidden direction:

```text
QueueService -> Bambu MQTT
Inventory    -> AMS native state
API DTO      -> raw Bambu payload
Generic UI   -> Bambu protocol field
```

### Suggested Bambu capability families

These are guidance, not a requirement to create all interfaces immediately:

```text
BambuAmsCapability
BambuDryingCapability
BambuHmsCapability
BambuKProfileCapability
BambuCalibrationCapability
BambuDualNozzleCapability
BambuVirtualPrinterCapability
BambuCloudCapability
```

Only create a capability when a real application workflow needs it.

## Multi-vendor adapter rule

PrintBuddy is primarily a structural reference for provider isolation.

For a new vendor family, FoxForge should require:

- a dedicated adapter package;
- a factory/registration entry in the composition/infrastructure layer;
- native-to-FoxForge state mapping inside the adapter;
- shared contract tests;
- vendor-specific tests for transport and error mapping;
- no change to common fleet/queue/inventory logic when existing capabilities are sufficient.

The following is considered an architecture smell:

```python
if printer.vendor == "bambu":
    ...
elif printer.vendor == "moonraker":
    ...
elif printer.vendor == "future_vendor":
    ...
```

inside common application services.

Vendor selection is expected in the composition root/registry. Vendor capability handling is expected behind typed capability boundaries.

## Queue and scheduler rule

FoxForge's queue is already safer than a simple "send job and mark running" model and must remain authoritative.

The scheduler may decide:

- which printer is eligible;
- priority and deadline ordering;
- material/nozzle/bed-size compatibility;
- maintenance or availability constraints;
- reservations and assignment policy.

The queue owns:

- persisted dispatch state;
- idempotency and duplicate prevention;
- external-start crash boundary;
- `INDETERMINATE` semantics;
- safe retry rules;
- lifecycle reconciliation.

PrintOps should therefore inform the **policy layer above the queue**, not replace queue safety.

Expected future flow:

```text
Job requirements
      |
      v
Scheduler / eligibility
      |
      v
Inventory reservation
      |
      v
Queue assignment
      |
      v
PrintExecutionCapability
      |
      v
Vendor adapter
```

The scheduler must not invoke MQTT, FTPS or Moonraker directly.

## Inventory and material-system rule

FoxForge inventory owns the durable spool record.

Recommended domain concepts:

```text
Material
Spool
Location
Assignment
Reservation
MassAdjustment
Consumption
Waste
Correction
```

Printer adapters expose physical material-system state:

```text
Printer
  `-- MaterialSystem
       `-- Slot/source ID
            `-- native material state
```

Inventory then associates a FoxForge spool with that physical slot/source.

This preserves history when a spool moves between:

```text
shelf -> X2D AMS tray -> external holder -> Moonraker printer -> shelf
```

Do not insert a FoxForge `spool_id` into raw/native printer state.

## Event-driven application rule

New automation should prefer normalized application events over feature-specific polling loops.

Potential normalized events include:

```text
ConnectionChanged
PrinterStateChanged
JobStateChanged
JobProgressChanged
PrintCompleted
PrintFailed
MaterialSlotsChanged
SpoolAssigned
SpoolMoved
SpoolConsumed
InventoryCorrected
```

Important consumer requirements:

- duplicate events must be safe;
- reconnect replay must be safe;
- late completion events must be safe;
- app restart must not double-charge material;
- a queue receipt or remote-job identity must be matched before terminal changes are applied.

### Minimum event tests

For any event-driven worker or projection, add tests for:

1. first delivery;
2. duplicate delivery;
3. replay after restart;
4. late/out-of-order delivery where relevant;
5. mismatched printer/job identity;
6. persisted idempotency state.

## Frontend rule

FoxForge's frontend is not a port of any upstream UI.

Use upstream projects as product/interaction references:

- Bambuddy for detailed Bambu printer/AMS/HMS workflows;
- PrintOps for operational/farm/warehouse workflows;
- PrintBuddy for multi-printer presentation ideas.

But new frontend code must consume FoxForge API models and capability descriptors.

A useful target shape is:

```text
frontend/src/
├── app/
├── features/
│   ├── printers/
│   ├── queue/
│   ├── inventory/
│   ├── materials/
│   └── farm/
├── vendor/            # introduce as deep vendor UI grows
│   └── bambu/
├── data/
└── shared/
```

The exact folders may evolve. The important boundary is semantic:

- generic features use normalized FoxForge data;
- vendor extensions are capability-gated;
- unsupported controls remain absent/disabled rather than simulated;
- frontend code never imports backend Python or vendor-native payload definitions.

## Provenance workflow

Before copying or adapting upstream implementation code, classify the change.

### Inspired

Use when an idea, workflow or product behavior is studied but the implementation is newly written.

PR note example:

```text
Upstream reference: PrintOps scheduler workflow
Classification: inspired
Implementation: newly written FoxForge code
```

### Derived

Use when code structure/logic is materially adapted from upstream.

PR must record:

```text
Upstream repository
Upstream commit/tag
Upstream file/path
Upstream license
FoxForge destination path
Classification: derived
Summary of modifications
Preserved copyright/license notice location
```

### Copied

Use when code is copied with minimal modification. Record the same information as `derived`, with especially careful preservation of notices.

Do not remove upstream notices merely because FoxForge itself is AGPL-3.0-only.

## Review checklist for architecture-significant PRs

Before merge, reviewers should be able to answer **yes** to the relevant items:

- Does common/domain/application code remain free of vendor protocol imports?
- Is the new feature attached to the smallest appropriate capability boundary?
- If it is Bambu-specific, does it remain Bambu-specific rather than expanding the base printer interface?
- If it is promoted to common, can its semantics be described without naming a vendor?
- Does queue work preserve `INDETERMINATE`, receipt and safe-retry behavior?
- Does inventory retain FoxForge spool identity independently of printer state?
- Does scheduler/farm logic depend only on application contracts and persisted state?
- Does the frontend consume normalized FoxForge contracts and capability state?
- Are event/replay/idempotency failure cases covered where relevant?
- Is upstream provenance documented for derived/copied material?
- Are acceptance criteria and tests included?
- Is hardware validation clearly separated from CI/mock/integration validation?

## Acceptance criteria by work type

### New printer adapter

- Shared adapter contract tests pass.
- No existing vendor package is imported.
- Existing `FleetService`, queue core and inventory core do not need vendor branches.
- Unsupported capabilities are absent rather than stubbed with misleading behavior.
- Reconnect and normalized error behavior are tested.

### New Bambu-only capability

- Capability is not added to base `PrinterAdapter` without promotion justification.
- Native state/transport details stay in Bambu infrastructure.
- API/read models expose only the required FoxForge-facing representation.
- Generic frontend code remains vendor-neutral.
- Bambuddy provenance is documented if implementation is derived/copied.
- Physical validation requirements are listed.

### New scheduler/farm feature

- Scheduler does not import vendor adapters/transports.
- Queue safety semantics remain unchanged.
- Eligibility/assignment policy has deterministic unit tests.
- Persistence/lease/idempotency rules are defined before multi-process execution.
- Material reservation behavior is explicit where applicable.

### New automatic spool accounting feature

- Consumption is idempotent across restart/replay.
- Printer/job identity is validated before ledger mutation.
- Estimated versus actual/reconciled usage semantics are explicit.
- Exact `Decimal` inventory guarantees are preserved.
- The feature works without knowing the vendor protocol payload shape.

## Upstream research refresh policy

Upstream projects change independently of FoxForge.

When revisiting an upstream feature:

1. record the repository and exact commit reviewed;
2. compare new upstream behavior with the current FoxForge ADRs;
3. adopt improvements only if they preserve FoxForge boundaries;
4. create a new ADR or amend an existing one only when the architectural decision itself changes;
5. do not silently change FoxForge architecture merely because upstream reorganized its code.
