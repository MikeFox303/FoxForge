# Material topology capability

- **Status:** Pre-Alpha 5 implementation contract
- **Capability:** `foxforge.material_topology` v1
- **Related:** `material_system`, `print_execution`, Bambu adapter foundation, interface refactor direction

## Purpose

FoxForge must distinguish **what material sources physically exist** from **where those sources can feed**.

`foxforge.material_system` remains the vendor-neutral observation contract for material units, slots, presence and detected material. It is intentionally not extended with Bambu-specific nozzle or AMS routing fields.

`foxforge.material_topology` is a separate optional read capability for the routing graph between existing material source slots and printer toolheads.

This separation keeps common printer abstractions reusable for Moonraker and future vendors while allowing deep Bambu dual-nozzle behavior to remain visible and safe.

## v1 model

A topology snapshot contains:

- stable opaque toolhead IDs plus optional display labels;
- one optional route record per material source slot;
- route kind:
  - `fixed` — the source is authoritatively bound to exactly one toolhead;
  - `dynamic` — the source can reach a known set of toolheads through a dynamic routing device;
  - `unknown` — FoxForge cannot prove the route and must not guess;
- observation timestamp and stale state.

Source identities reuse the existing opaque `MaterialSlotId` values from `material_system`. The common model does not expose Bambu AMS IDs, `info` bitfields, FTS inlet values or other vendor-wire fields.

## Bambu mapping rules

The Bambu adapter is solely responsible for interpreting Bambu telemetry.

For direct AMS routing, the adapter may publish a fixed route only when the printer's AMS metadata reports a recognized extruder ID. Current observed/publicly studied semantics use AMS `info` bits 8–11 where `0` and `1` are concrete extruder identities. Other values are not coerced to an extruder.

In particular, `0xE` is not treated as a fixed route. It is associated with uninitialized/dynamic Filament Track Switch routing in the upstream behavior studied for this work. Until FoxForge has sufficient FTS telemetry to prove reachable toolheads, such a source is reported as `unknown` rather than silently assigned to a nozzle.

For dual external feeds, FoxForge publishes fixed side routing only when the physical pair is proven by simultaneous external source IDs `254` and `255`:

```text
source 254 -> left toolhead  / extruder 1
source 255 -> right toolhead / extruder 0
```

A lone source `254` is **not** enough evidence for a left toolhead because single-nozzle Bambu printers also use the ordinary external source identity. It therefore remains side-neutral/unknown unless the dual pair is observed.

## Toolhead identity

Bambu adapter toolhead IDs are opaque to generic consumers:

```text
bambu:toolhead:0
bambu:toolhead:1
```

Human-facing labels such as `Right toolhead` and `Left toolhead` are adapter-provided display metadata. Generic application/UI code must not infer Bambu routing from the printer model string.

## Events and read model

Bambu advertises `foxforge.material_topology` only when the adapter implements the capability. The fleet read model exposes an optional `materialTopology` alongside `materialSystem`.

Routing-only changes emit `material_topology_changed` so realtime clients can invalidate the fleet snapshot even when slot material contents did not change.

Moonraker does not advertise this capability merely because the common contract exists.

## Printer Detail UI contract

The generic Printer Detail `Materials` view renders topology only from the typed `materialTopology` read model. It does not inspect `vendor`, `model`, Bambu AMS IDs, external source IDs or protocol fields.

Presentation rules:

- source names are resolved from `material_system` by opaque `sourceSlotId` when a friendly slot label is available;
- toolhead names come from topology display metadata, with physical position used only as a generic label fallback;
- `fixed`, `dynamic` and `unknown` remain visually distinct rather than being flattened into a single connection type;
- `unknown` routes never display a guessed toolhead;
- unresolved toolhead IDs are visibly incomplete rather than silently discarded;
- stale topology is marked as last-reported data and must not look equivalent to a fresh route;
- absence of the capability is shown as unavailable topology, not inferred from the printer model;
- responsive layout must preserve route/source/target readability without horizontal viewport overflow.

This UI remains observational. It does not choose print bindings or authorize dispatch. The queue routing compiler remains the authority for fresh material/toolhead validation immediately before a physical print side effect.

## Safety rules

1. Unknown routing is represented explicitly; it is never defaulted to toolhead/extruder 0.
2. A fixed route must have exactly one target toolhead.
3. A dynamic route must identify at least one known reachable toolhead.
4. Route targets must exist in the same topology snapshot.
5. One source slot has at most one route record.
6. Vendor wire identifiers remain inside the adapter package.
7. The topology capability is observational. Print-start validation remains the responsibility of the print execution/print-plan path and must revalidate fresh topology before a side effect.

## Pre-Alpha 5 acceptance fixture

The current physical X2D fixture is:

```text
X2D
├─ AMS 2 Pro
│  ├─ A1 PETG
│  ├─ A2 PETG
│  ├─ A3 PETG
│  └─ A4 PETG
├─ External Left  -> left toolhead  -> empty
└─ External Right -> right toolhead -> PLA
```

Automated tests must prove at minimum:

- dual external `254` + `255` fixed routing;
- single external `254` remains unknown;
- authoritative AMS extruder `0`/`1` mapping;
- `0xE`/unsupported AMS routing remains unknown;
- partial AMS updates that omit routing metadata preserve the last authoritative reading;
- an explicit later unsupported/uninitialized routing value clears the prior fixed route;
- Bambu advertises the capability while Moonraker does not;
- fleet/API serialization contains only common topology fields;
- Printer Detail renders fixed Left/Right topology from common fields only;
- stale and unknown routes are visibly non-authoritative;
- phone viewport rendering does not overflow horizontally.

Physical validation of the final Alpha 5 candidate is still required on Raspberry Pi 5 + Umbrel + the real X2D.

## Upstream provenance

Implementation classification for this design: **Inspired / newly written FoxForge code**.

Behavior was studied from `maziggy/bambuddy` at commit `9b2c49d866ae1ddc63f23cea53461ff19cb86346`, particularly its treatment of AMS extruder mapping, dual external sources and FTS fail-closed routing. No upstream implementation code is copied by this design.
