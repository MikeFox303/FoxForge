# Immutable 3MF print-plan inspection

Status: implemented for the Pre-Alpha 5 routing path; Candidate 5 published and physical X2D validation pending.

## Decision

FoxForge inspects a print plan only from a previously staged, content-addressed `LocalPrintArtifact`. The inspection API accepts an artifact SHA-256 identifier, never an arbitrary server filesystem path.

For sliced Bambu-compatible 3MF files, logical material requirements come from the embedded `Metadata/plate_N.gcode` members that would actually be selected by the Bambu `project_file` command.

`Metadata/project_settings.config` can enrich known material requirements with optional family/color/profile metadata and can also carry dual-toolhead translation metadata used by the separate toolhead parser. Those two roles have different safety semantics:

- malformed descriptive material metadata does not invent a logical material requirement;
- present-but-invalid toolhead-routing metadata must not be treated as if no toolhead intent existed.

## Why inspect executable plate G-code

Bambu Studio / Orca 3MF projects can contain overlapping metadata representations. Numeric `M620 S...` selections in the embedded sliced plate G-code are the immutable evidence FoxForge uses for the logical material indices required by each plate:

- `M620 S0A` means project material index `0` is required;
- suffixes after the numeric index do not change the logical index;
- `M620 S255` is unload and is ignored;
- a plate with no numeric material selection is routing-blocked;
- an out-of-range material index blocks that plate even when other valid indices exist.

## Toolhead expectation precedence

For dual-toolhead 3MFs, FoxForge derives optional expected physical toolhead positions conservatively:

1. actual plate `slice_info.config` filament group assignments are authoritative when present;
2. an optional group-to-extruder table is applied before `physical_extruder_map`;
3. `physical_extruder_map` converts slicer extruders to physical toolhead positions;
4. `filament_nozzle_map` is fallback-only when the selected plate contains no actual group assignment.

Actual plate assignments therefore override project fallback preferences.

A malformed fallback does not poison a plate with complete valid actual assignments because the fallback is unused. A plate that needs fallback cannot use a malformed fallback.

## Missing versus invalid toolhead metadata

These states are intentionally different.

**Missing metadata** means no usable dual-toolhead intent is present. FoxForge may leave `expected_toolhead_position=None`; the later compiler can still allow an explicit source whose current route proves exactly one toolhead.

**Invalid metadata** means relevant metadata exists but cannot be trusted. Examples include:

- ambiguous duplicate `project_settings.config` or `slice_info.config` members;
- encrypted or oversized routing metadata;
- malformed/non-object `project_settings.config`;
- invalid `physical_extruder_map`;
- malformed `filament_nozzle_map` when fallback is required;
- partial or contradictory plate filament groups;
- invalid group/nozzle tables;
- forbidden DTD/entity declarations or malformed XML in `slice_info.config`.

These conditions produce plate-scoped `TOOLHEAD_METADATA_INVALID`. The routing compiler treats that issue as a blocker even when the selected physical source has a fixed route. A fixed physical route proves source reachability; it does not prove slicer intent.

This distinction closed the Candidate 4 audit gap where parser failure could otherwise appear indistinguishable from genuinely absent toolhead intent. Candidate 5 contains the fix and is the immutable target for new physical evidence.

## Immutability boundary

The inspector:

1. receives a `LocalPrintArtifact` produced by the artifact store;
2. opens that exact staged file descriptor;
3. verifies size and SHA-256 against staged metadata;
4. parses the ZIP through the same open descriptor without extracting members to disk;
5. verifies size and SHA-256 again after inspection.

A file that disappears, changes size/hash, becomes unreadable, or otherwise cannot be inspected safely is rejected and must be re-staged.

## Bounded parsing

Inspection is deliberately bounded for self-hosted Raspberry Pi / Umbrel deployments:

- bounded ZIP member count and member-name length;
- bounded `project_settings.config` and `slice_info.config` reads;
- bounded per-plate uncompressed G-code size;
- streaming G-code parsing;
- bounded individual G-code line length;
- no ZIP extraction to the filesystem;
- encrypted/unsupported required members fail closed.

These are FoxForge safety limits, not Bambu protocol constants.

## Contract

An `ArtifactPrintPlan` contains:

- immutable artifact identity and SHA-256;
- zero-based plate indices;
- per-plate logical material requirements;
- optional project material family/color/profile metadata;
- optional expected physical toolhead positions;
- per-plate `ready_for_routing`;
- explicit warning/blocking issues;
- aggregate `ready_for_routing` for whole-plan display/status.

The HTTP read is:

`GET /api/v1/artifacts/{artifactId}/print-plan`

It uses the existing `queue.write` operator permission. It is read-only and does not require command idempotency.

## Plate-scoped routing semantics

Aggregate `ready_for_routing` describes the whole plan. Dispatch safety is selected-plate scoped:

- multi-plate jobs require an explicit plate selection;
- the selected plate must be routing-ready;
- global blockers apply to all plates;
- selected-plate `TOOLHEAD_METADATA_INVALID` blocks;
- a blocking issue belonging only to another unselected plate does not invalidate a safe selected plate.

The browser review and server compiler follow the same rule.

## Relationship to material topology

`foxforge.material_topology` describes current physical source -> toolhead reachability. The print plan describes immutable logical material requirements and optional slicer toolhead intent.

The routing compiler joins them explicitly:

`3MF material requirement -> explicit FoxForge material source -> current topology route -> expected/proven toolhead -> Bambu native mapping`

Unknown, ambiguous, stale, contradictory or invalid joins remain blockers. No default-to-toolhead-0 behavior is permitted.

## Candidate 5 validation boundary

New physical evidence must use the exact Candidate 5 application/image identity recorded in `docs/testing/pre-alpha-5-bambu-physical-validation.md`. Candidate 1/2/3/4 evidence is historical and cannot satisfy Candidate 5.

The no-print sections of that runbook must pass before the first physical Start. During selected-plate review, physical validation must prove both sides of the safety rule:

- invalid selected-plate toolhead metadata remains blocked even against a fixed physical source route;
- a blocker belonging only to another unselected plate does not poison a safe selected plate.

Any application-code change after Candidate 5 invalidates affected physical evidence and requires another immutable candidate.

## P3 accounting remains frozen

Although Bambu 3MF metadata can contain `used_g`, estimated filament length and related values, this milestone does not apply them to inventory. Automatic filament accounting remains frozen until the Alpha 5 physical connection/control/real-print gate is complete.

## Upstream provenance

Classification: **Inspired**.

Behavior reviewed against Bambuddy `maziggy/bambuddy` at `9b2c49d866ae1ddc63f23cea53461ff19cb86346`, including plate-scoped G-code selection, `M620` material changes, project filament metadata and dual-toolhead grouping/nozzle mapping semantics. No upstream implementation code is copied into FoxForge.

## Acceptance criteria

- [x] only staged content-addressed artifacts can be inspected through the API;
- [x] artifact bytes are SHA-256 checked before and after parsing;
- [x] material requirements are plate-scoped;
- [x] actual plate group assignments override fallback nozzle preferences;
- [x] missing single-toolhead metadata does not invent a dual-toolhead expectation;
- [x] present-but-invalid toolhead metadata is explicitly reported and cannot masquerade as absence;
- [x] malformed fallback blocks only when the plate relies on fallback;
- [x] unknown/out-of-range logical material requirements fail closed;
- [x] unsafe/ambiguous required structures do not reach dispatch;
- [x] inspection is authenticated and read-only;
- [x] no P3 consumption mutation is introduced;
- [x] Candidate 5 immutable source/image/Umbrel identity published;
- [ ] Candidate 5 passes Raspberry Pi 5 + Umbrel + X2D + AMS 2 Pro no-print validation;
- [ ] first real print evidence passes before final Alpha 5.
