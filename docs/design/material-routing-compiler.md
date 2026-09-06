# Material routing compiler

Status: implementation foundation for Pre-Alpha 5.

## Decision

FoxForge compiles print-material routing as a vendor-neutral, read-only application step before any printer adapter is
allowed to dispatch a print.

The compiler joins four independent pieces of evidence:

1. immutable plate-scoped requirements from the staged print plan;
2. explicit operator-selected `MaterialBinding` source slots;
3. the printer's current `MaterialSystemSnapshot`;
4. the printer's current `MaterialTopologySnapshot`.

It produces either a complete set of bindings with a proven `toolhead_id`, or blockers and **no partial compiled
bindings**.

The compiler never automatically chooses an AMS, external source, color substitute or toolhead.

## Inputs

`compile_material_routing(...)` accepts:

- `ArtifactPrintPlan`;
- optional `PrintArtifactSelection`;
- explicit `MaterialBinding` values;
- `MaterialSystemSnapshot`;
- `MaterialTopologySnapshot`.

`MaterialBinding.toolhead_id` is compiler-owned. Queue/API clients may choose the physical source slot, but they may
not provide a toolhead identity through the enqueue API.

## Plate rules

- a single-plate plan may omit an explicit plate selection;
- a multi-plate plan must select one plate explicitly;
- a selected plate must exist and be `ready_for_routing`;
- a selected plate with `TOOLHEAD_METADATA_INVALID` is blocked even when its chosen source has a fixed route;
- bindings must cover exactly the material indices used by that plate;
- bindings for materials belonging only to other plates are rejected.

The extra toolhead-metadata rule prevents topology from masking corrupt or partial slicer intent on dual-nozzle
printers. A fixed physical route proves where a source can go; it does not prove that the sliced plate intended that
toolhead.

This intentionally differs from silently defaulting to plate 1. A default that is convenient for a transport is not
sufficient evidence for a safety gate.

## Source rules

For every required material:

- the explicitly selected slot must exist in the current material-system snapshot;
- its presence must be positively `LOADED`; `EMPTY` and `UNKNOWN` are blockers;
- when the immutable print plan names a material family, the loaded source must also report a family;
- known material families are compared case-insensitively and must match;
- color is descriptive evidence, not a hard routing constraint after the operator has explicitly selected a source.

Automatic color/type matching remains outside this compiler.

## Topology rules

The material-system and topology snapshots must refer to the same printer and both must be fresh.

For every selected source:

- a topology route must exist;
- `MaterialRouteKind.UNKNOWN` is a blocker;
- if the print plan names an expected toolhead position, that position must resolve to exactly one reported toolhead
  and the selected source must be able to reach it;
- if the print plan does not name a toolhead, the selected source route itself must resolve to exactly one toolhead;
- a route that can reach several toolheads without additional immutable evidence is ambiguous and is blocked.

A previously compiled binding is idempotent only while current evidence resolves to the same `toolhead_id`. If the
route changes, the compiler returns `compiled_route_changed` rather than silently rewriting a persisted dispatch
decision.

## Fail-closed output

`MaterialRoutingCompilation` contains:

- the resolved zero-based plate index;
- complete compiled bindings when eligible;
- typed blockers when not eligible.

Blocked compilations expose an empty binding tuple. Downstream code must never consume a partially compiled route.

Representative blockers include:

- plate selection missing/not found;
- print-plan or unsafe toolhead-metadata blocker;
- missing/extra material binding;
- stale or cross-printer snapshots;
- unknown/unloaded source;
- unknown or mismatched material family;
- unknown topology route;
- unknown/ambiguous/incompatible toolhead;
- changed previously compiled route.

## Bambu Lab relationship

The compiler itself has no Bambu adapter dependency.

For X2D/H2D-class printers, earlier FoxForge layers translate Bambu observations into vendor-neutral material-system
and topology snapshots, while immutable 3MF inspection may expose an expected physical toolhead position. The compiler
only joins those contracts.

A later Bambu-specific dispatch gate will revalidate the compiled `toolhead_id` immediately before submit and encode
the required native nozzle/toolhead mapping. Until that layer exists and passes tests, this compiler does not enable
physical print dispatch by itself.

## Queue integration

This PR intentionally keeps the compiler pure. The following integration slice must:

1. inspect the staged artifact immediately before queue assessment/dispatch;
2. resolve current material-system and topology capabilities from the target printer;
3. compile the explicit source bindings;
4. persist the complete compiled bindings before any submit side effect;
5. map routing blockers into normalized queue assessment blockers;
6. compare enqueue replays using client-owned intent only, ignoring compiler-owned `toolhead_id`;
7. recompile before dispatch so stale/changed topology cannot reuse an old decision silently.

## Acceptance criteria

- [x] compiler has no vendor adapter imports;
- [x] multi-plate plans require explicit selection;
- [x] binding coverage is exact for the selected plate;
- [x] invalid plate toolhead metadata blocks even a fixed physical route;
- [x] stale snapshots fail closed;
- [x] unknown/unloaded sources fail closed;
- [x] known material-family mismatch fails closed;
- [x] color mismatch alone does not block an explicit source choice;
- [x] unknown/ambiguous/incompatible routes fail closed;
- [x] changed compiled toolhead fails closed;
- [x] blocked compilations never expose partial compiled bindings;
- [ ] queue assessment persists compiled bindings before submit;
- [ ] Bambu submit revalidates and encodes compiled toolhead mapping;
- [ ] immutable Alpha 5 candidate is physically validated on X2D before the first real production print workflow is accepted.
