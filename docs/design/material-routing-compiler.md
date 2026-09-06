# Material routing compiler

Status: implemented for the Pre-Alpha 5 routing path; physical X2D validation pending a replacement immutable candidate.

## Decision

FoxForge compiles print-material routing as a vendor-neutral application step before any printer adapter is allowed to dispatch a print.

The compiler joins four independent pieces of evidence:

1. immutable plate-scoped requirements from the staged print plan;
2. explicit operator-selected `MaterialBinding` source slots;
3. the printer's current `MaterialSystemSnapshot`;
4. the printer's current `MaterialTopologySnapshot`.

It produces either a complete set of bindings with a proven `toolhead_id`, or blockers and **no partial compiled bindings**.

The compiler never automatically chooses an AMS, external source, color substitute or toolhead.

## Inputs

`compile_material_routing(...)` accepts:

- `ArtifactPrintPlan`;
- optional `PrintArtifactSelection`;
- explicit `MaterialBinding` values;
- `MaterialSystemSnapshot`;
- `MaterialTopologySnapshot`.

`MaterialBinding.toolhead_id` is compiler-owned. Queue/API clients may choose the physical source slot, but they may not provide a toolhead identity through the enqueue API.

## Plate rules

- a single-plate plan may omit an explicit plate selection;
- a multi-plate plan must select one plate explicitly;
- the selected plate must exist and be `ready_for_routing`;
- blocking issues belonging only to another unselected plate do not invalidate an otherwise safe selected plate;
- global blocking issues still apply to every plate;
- a selected plate with `TOOLHEAD_METADATA_INVALID` is blocked even when its chosen source has a fixed route;
- bindings must cover exactly the material indices used by that plate;
- bindings for materials belonging only to other plates are rejected.

The extra toolhead-metadata rule prevents topology from masking corrupt or partial slicer intent on dual-nozzle printers. A fixed physical route proves where a source can go; it does not prove that the sliced plate intended that toolhead.

Missing toolhead metadata and invalid toolhead metadata are therefore different states. A 3MF that simply does not identify a toolhead can still use an otherwise unambiguous proven source route. Metadata that is present but malformed, ambiguous, encrypted, oversized or internally inconsistent is not treated as absence and blocks routing for the affected plate.

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
- if the print plan names an expected toolhead position, that position must resolve to exactly one reported toolhead and the selected source must be able to reach it;
- if the print plan does not name a toolhead, the selected source route itself must resolve to exactly one toolhead;
- a route that can reach several toolheads without additional immutable evidence is ambiguous and is blocked.

A previously compiled binding is idempotent only while current evidence resolves to the same `toolhead_id`. If the route changes, the compiler returns `compiled_route_changed` rather than silently rewriting a persisted dispatch decision.

## Queue integration

Queue integration is implemented.

For routed 3MF requests, QueueService:

1. inspects the immutable staged artifact;
2. obtains current material-system and topology snapshots;
3. runs the routing compiler;
4. persists the complete compiler-owned bindings before adapter assessment or any submit side effect;
5. maps compiler failures into normalized assessment blockers;
6. compares enqueue idempotency replays using client-owned source intent while ignoring only server-owned `toolhead_id`;
7. recompiles on dispatch so stale or changed topology cannot silently reuse an old route.

G-code/Moonraker execution remains outside this 3MF routing gate.

## Bambu Lab dispatch defense

Bambu native revalidation is implemented as defense in depth.

Immediately before transport submission the adapter uses one native state snapshot to verify that:

- the bound source still exists;
- the selected tray/source is still positively present;
- topology is fresh;
- the source can still reach the compiler-owned toolhead;
- the toolhead maps to an allowed native nozzle index.

Only a complete validated mapping becomes `project_file.nozzle_mapping`. External source IDs 254/255 remain `-1` in flat `ams_mapping`, retain their real source IDs in `ams_mapping2`, and receive a nozzle only from the compiler-owned toolhead decision.

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

## Candidate boundary

Candidate 4 exposed the complete routing stack but a later release-readiness audit found that some present-but-invalid `project_settings.config` / toolhead mapping states could be converted into apparent metadata absence before the compiler saw them. PR #145 closes that gap and also aligns browser review with selected-plate semantics.

Candidate 4 must not be used for the first real print after this finding. A new immutable application/image/Umbrel candidate is required after the fix passes exact-head gates.

## Acceptance criteria

- [x] compiler has no vendor adapter imports;
- [x] multi-plate plans require explicit selection;
- [x] binding coverage is exact for the selected plate;
- [x] invalid selected-plate toolhead metadata blocks even a fixed physical route;
- [x] present-but-invalid toolhead metadata is not silently converted into absence;
- [x] blocking issues on an unselected plate do not poison a safe selected plate;
- [x] stale snapshots fail closed;
- [x] unknown/unloaded sources fail closed;
- [x] known material-family mismatch fails closed;
- [x] color mismatch alone does not block an explicit source choice;
- [x] unknown/ambiguous/incompatible routes fail closed;
- [x] changed compiled toolhead fails closed;
- [x] blocked compilations never expose partial compiled bindings;
- [x] queue assessment persists compiled bindings before submit;
- [x] Bambu submit revalidates and encodes compiled toolhead mapping;
- [ ] replacement immutable candidate passes Raspberry Pi 5 + Umbrel + X2D + AMS 2 Pro no-print gate;
- [ ] first real print and guarded job-control evidence pass before final Alpha 5.
