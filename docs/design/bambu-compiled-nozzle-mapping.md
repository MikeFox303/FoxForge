# Bambu compiled nozzle mapping gate

Status: Pre-Alpha 5 implementation contract.

## Decision

FoxForge must derive Bambu `project_file.nozzle_mapping` only from the compiler-owned physical toolhead decision that has already passed the vendor-neutral queue routing gate.

The Bambu adapter must not infer a nozzle from AMS ID, tray ID, material color, or a hard-coded left/right fallback.

## Upstream provenance

Classification: **Inspired**, newly written FoxForge code.

Behavior was reviewed against Bambuddy at commit `9b2c49d866ae1ddc63f23cea53461ff19cb86346`. Bambuddy documents `nozzle_mapping` as a per-filament list of physical nozzle position IDs carried in BambuStudio `project_file` MQTT commands and preserved for dispatch. Its dual-nozzle model notes identify ordinary Bambu MQTT nozzle/extruder indices as `0 = right` and `1 = left`.

FoxForge does not copy Bambuddy implementation code. The FoxForge implementation instead derives the native index from its own `MaterialTopologySnapshot` after the vendor-neutral routing compiler has produced `MaterialBinding.toolhead_id`.

## Adapter revalidation

For every Bambu material binding supplied to `BambuPrintExecutionCapability`:

- the physical source slot must still exist in the current native state;
- a compiler-owned `toolhead_id` must be present;
- the current Bambu material topology must still route that source to the compiled toolhead;
- the compiled toolhead must resolve to one valid native nozzle index (`0` or `1`).

Any mismatch is a `material_binding_invalid` assessment blocker. The transport is not called.

Requests without material bindings retain the existing legacy/native behavior and do not emit `nozzle_mapping`. The queue routing gate introduced before this slice ensures normal routed 3MF jobs cannot omit required bindings.

## Single-snapshot submit rule

`submit()` obtains one `PrinterSnapshot` and one `BambuNativeState` for its final adapter assessment. Material-route revalidation and construction of `BambuNativePrintRequest` use that same native state.

This ordering prevents the adapter from doing the following unsafe sequence:

1. validate compiled toolhead against native state A;
2. observe a topology change to native state B;
3. construct the MQTT material/nozzle route from state B without revalidating the compiler decision.

The transport can still observe a later physical state change after the snapshot, but FoxForge does not introduce an internal assessment/construction race.

## Native DTO boundary

The vendor-neutral `toolhead_id` does not enter the LAN codec.

`BambuPrintExecutionCapability` translates a validated toolhead into `BambuNativeMaterialRoute.nozzle_index`. The native route therefore contains:

- logical material index;
- Bambu AMS ID;
- Bambu tray ID;
- optional native nozzle index.

A `BambuNativePrintRequest` rejects a partial nozzle mapping: either every native material route has a nozzle index or none does.

## MQTT encoding

When every native material route has a validated nozzle index, `build_project_file_command()` adds:

`nozzle_mapping: list[int]`

The list is aligned by logical material index, matching the existing `ams_mapping` alignment. Sparse logical material indices are represented by `-1` placeholders.

`ams_mapping` and `ams_mapping2` keep their existing behavior:

- regular AMS slots retain flat `ams_mapping` values;
- external AMS IDs `254` and `255` remain `-1` in flat `ams_mapping`;
- their real IDs remain present in `ams_mapping2`;
- nozzle mapping comes from the compiled toolhead, never from the external AMS number.

Legacy native requests with no nozzle indices do not receive a `nozzle_mapping` field.

## Defense in depth

The complete Pre-Alpha 5 Bambu route now has three independent checks:

1. immutable 3MF inspection derives plate-scoped toolhead expectations;
2. the vendor-neutral routing compiler proves source -> toolhead and persists the compiler-owned binding before adapter assessment;
3. the Bambu adapter revalidates the persisted toolhead against one current native topology snapshot before constructing `project_file`.

Bambu dispatch idempotency continues to include `toolhead_id` in the request fingerprint. A confirmed `dispatch_id` cannot be replayed with a different compiled toolhead.

## Non-goals

This slice does not:

- automatically choose AMS/external sources;
- rewrite slicer toolhead intent;
- add rack-swap nozzle IDs beyond the current 0/1 dual-toolhead topology contract;
- change calibration defaults;
- change FTP/project upload behavior;
- implement P3 filament accounting;
- authorize a real production print test by itself.

## Acceptance criteria

- [x] Bambu material binding without compiler-owned toolhead is blocked before transport;
- [x] compiled toolhead incompatible with current native topology is blocked before transport;
- [x] adapter translates validated toolhead position to native nozzle index;
- [x] adapter uses one native snapshot for final revalidation and request construction;
- [x] native print request rejects partial nozzle mappings;
- [x] LAN `project_file` emits nozzle mapping only for complete native mappings;
- [x] nozzle mapping is aligned by material index;
- [x] external 254/255 AMS routing retains real IDs in `ams_mapping2` and uses compiled nozzle indices;
- [x] legacy native requests without nozzle indices retain the old payload shape;
- [ ] Ruff + Python 3.12/3.13 contract/unit suite green;
- [ ] security, deployment-auth, container and Browser acceptance green;
- [ ] real X2D validation is performed only after this gate and the remaining Pre-Alpha 5 command/UI checks are merged.
