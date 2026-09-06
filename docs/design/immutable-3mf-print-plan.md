# Immutable 3MF print-plan inspection

Status: implemented for the Pre-Alpha 5 routing foundation.

## Decision

FoxForge inspects a print plan only from a previously staged, content-addressed `LocalPrintArtifact`.
The inspection API accepts an artifact SHA-256 identifier, never an arbitrary server filesystem path.

For sliced Bambu-compatible 3MF files, the first routing gate derives plate material requirements from the embedded
`Metadata/plate_N.gcode` members that would actually be selected by the Bambu `project_file` command.

`Metadata/project_settings.config` is metadata-only at this stage. It may enrich a material requirement with the
project material family, color and filament profile name, but malformed or missing project metadata never causes
FoxForge to invent a material index.

## Why inspect executable plate G-code

Bambu Studio / Orca 3MF projects can contain several overlapping metadata representations. FoxForge needs a small,
high-confidence contract before it is allowed to compile physical AMS/external mappings.

The embedded sliced plate G-code is the closest available immutable evidence for the logical material slots used by
that plate. Numeric `M620 S...` selections are therefore treated as the authoritative material-index evidence for
this first gate:

- `M620 S0A` means project material index `0` is required;
- suffixes after the numeric index do not change the logical index;
- `M620 S255` is unload and is ignored;
- a plate with no numeric material selection is not guessed and remains routing-blocked;
- an out-of-range material index makes that plate routing-blocked even if other valid indices are present.

This is intentionally narrower than Bambuddy's broader 3MF toolkit. The implementation is newly written FoxForge
code, behaviorally informed by Bambuddy's plate-scoped G-code selection and project-filament parsing.

## Immutability boundary

The inspector:

1. receives a `LocalPrintArtifact` produced by the artifact store;
2. opens that exact staged file descriptor;
3. verifies size and SHA-256 against staged metadata;
4. parses the ZIP through the same open descriptor without extracting members to disk;
5. verifies size and SHA-256 again after inspection.

A file that disappears, changes size, changes hash, becomes unreadable, or otherwise cannot be inspected safely is
rejected. The caller must re-stage it rather than continuing from stale evidence.

## Bounded parsing

Inspection is deliberately bounded for self-hosted Raspberry Pi / Umbrel deployments:

- bounded ZIP member count and member-name length;
- bounded `project_settings.config` size;
- bounded per-plate uncompressed G-code size;
- streaming G-code parsing instead of loading plate G-code into memory;
- bounded individual G-code line length;
- no ZIP extraction to the filesystem;
- encrypted/unsupported members are rejected when they affect required plate data.

These limits are safety bounds, not Bambu protocol constants.

## Contract

An `ArtifactPrintPlan` contains:

- immutable artifact identity and SHA-256;
- zero-based plate indices;
- per-plate logical material requirements;
- optional project material family/color/profile metadata;
- per-plate `ready_for_routing`;
- explicit warning/blocking issues;
- aggregate `ready_for_routing`.

The HTTP read is:

`GET /api/v1/artifacts/{artifactId}/print-plan`

It is authenticated with the existing `queue.write` operator permission. It does not require an idempotency key
because it is read-only and cannot enqueue or dispatch a print.

## Fail-closed rules

The plan is not routing-ready when:

- no `Metadata/plate_N.gcode` members exist;
- a selected plate has no numeric `M620` material requirement;
- a plate references an unsupported material index;
- plate G-code members are structurally ambiguous;
- staged artifact identity no longer matches the bytes being inspected.

Missing or malformed descriptive project metadata is a warning only when executable material indices are still
known. The later routing compiler must not use missing descriptive metadata as permission to guess a physical source.

## Relationship to material topology

`foxforge.material_topology` describes current physical source -> toolhead reachability.
This print-plan contract describes the immutable logical material requirements inside one staged artifact.

The next routing stage must join the two explicitly:

`3MF material requirement -> selected FoxForge material slot -> topology route -> Bambu native material route`

Unknown or incompatible joins must remain blockers. No default-to-toolhead-0 behavior is permitted.

## P3 accounting remains frozen

Although Bambu 3MF metadata can contain `used_g`, estimated filament length and related values, this milestone does
not ingest or apply them to inventory. Automatic filament accounting remains frozen until Pre-Alpha 5 connection,
control and real-print acceptance are complete.

## Upstream provenance

Classification: **Inspired**.

Reviewed behavior:

- Bambuddy `backend/app/utils/threemf_tools.py` at `9b2c49d866ae1ddc63f23cea53461ff19cb86346`;
- plate-scoped embedded G-code selection;
- project `filament_type` / `filament_colour` positional metadata;
- explicit handling of multi-plate material differences.

No Bambuddy implementation code is copied into FoxForge.

## Acceptance criteria

- [x] only staged content-addressed artifacts can be inspected through the API;
- [x] artifact bytes are SHA-256 checked before and after parsing;
- [x] single- and multi-plate material requirements are plate-scoped;
- [x] project material family/color/profile metadata is optional and non-authoritative;
- [x] unknown material requirements fail closed;
- [x] out-of-range indices fail closed without large allocations;
- [x] malformed/ambiguous 3MF structures do not reach dispatch;
- [x] inspection is authenticated and read-only;
- [x] no P3 consumption mutation is introduced;
- [ ] later routing compiler proves source/toolhead compatibility before creating Bambu mappings;
- [ ] physical X2D candidate verifies the final compiled plan before first print.
