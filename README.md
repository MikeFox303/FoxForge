# FoxForge

[![Release](https://img.shields.io/badge/pre--release-v0.1.0--alpha.4.3-orange)](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)
[![Alpha 5](https://img.shields.io/badge/Alpha%205-Candidate%206%20C6--11%20ready-yellow)](docs/project-status.md)
[![License](https://img.shields.io/badge/license-AGPL--3.0--only-blue)](LICENSE)
[![Platforms](https://img.shields.io/badge/Linux-amd64%20%7C%20arm64-lightgrey)](deployment/README.md)

**FoxForge is an open-source, self-hosted platform for managing mixed fleets of 3D printers through a vendor-independent core while preserving deep vendor-specific capabilities.**

Bambu Lab is the current primary integration target. Moonraker/Klipper is supported through the same common architecture, while material systems, queueing, filament accounting and future farm-management features remain capability-driven rather than tied to a single printer family.

> [!WARNING]
> FoxForge is early alpha software. It is suitable for development and controlled self-hosted testing, but it is **not production-ready**. CI, browser tests and QEMU container smoke are not physical printer validation.

## Release and Candidate 6 status

The latest published semantic pre-release is **[v0.1.0-alpha.4.3](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)**. Final **`v0.1.0-alpha.5` has not been published**.

Pre-Alpha 5 is tracked by [#115](https://github.com/MikeFox303/FoxForge/issues/115), with replacement Candidate 6 stabilization in [#154](https://github.com/MikeFox303/FoxForge/issues/154).

Current source state:

- Candidate 5 is historical/failed for Alpha 5 acceptance after real X2D testing exposed partial `push_status` and dual-external `vir_slot` compatibility gaps;
- those findings were fixed and locked by the Candidate 6 regression work;
- **C6-01 through C6-10 are integrated on `main`**;
- **C6-10 exact-main software acceptance passed** on `994e39fc442bf48fa6069f0750dc9e886af6f23b` in run `34308752322`;
- Candidate 6 has **not** been published or physically validated;
- **C6-11 is the next gate**: freeze one exact source SHA, publish the matching multi-architecture image/digest and Umbrel package, then authorize Candidate 6 physical validation.

The current Umbrel Store package is still the historical Candidate 5 package:

```text
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.5
Candidate 5 source: 0351c659f2d2845fb83bc0b1802c4d9ebeeef1f2
exact image: ghcr.io/mikefox303/foxforge:sha-0351c65@sha256:00c699effbe9b245a4916a8c301df5b67435d75dd42fad02cc5bbf0ca51aec39
```

It remains installable for continuity and historical diagnostics, but it is **not the new Candidate 6 acceptance target**. No Candidate 5 evidence may be relabeled as Candidate 6 evidence.

See the [Candidate 6 software gate contract](docs/testing/pre-alpha-5-candidate6-software-gate.md) and [current project status](docs/project-status.md).

## What current `main` provides

### Printer setup and fleet

- FoxForge-owned `PrinterAdapter` contracts with typed capability discovery;
- Bambu Lab LAN and Moonraker/Klipper adapters behind vendor-neutral application boundaries;
- application-managed Add / Update / Remove / Reconnect workflows;
- staged Add Printer **Provider → Connection → Identity → Verify** with exact-payload verification invalidation before Save;
- test-before-save for Add and Update, with rollback to the previous working adapter/configuration on failed replacement;
- bounded Bambu LAN discovery with manual fallback;
- restart-safe reconnect supervision with bounded backoff/jitter and secret-safe diagnostics.

### Deep Bambu Lab support

- MQTT/TLS live-state transport;
- FTPS project storage and fail-closed `project_file` print-start semantics;
- sparse/incremental X2D report handling, including valid initial `push_status` without mandatory `gcode_state`;
- AMS-family and external material-source observation;
- `print.vir_slot` support for X2/H2 dual external sources with typed left/right topology;
- typed `foxforge.material_topology` routes with fixed/dynamic/unknown/stale states;
- common `foxforge.thermal_telemetry` v1 with X2/H2 thermal data;
- compiler-owned `ams_mapping`, `ams_mapping2` and `nozzle_mapping` generation from proven routing intent;
- guarded Pause / Resume / Cancel using the exact observed vendor-job identity;
- optional MQTT and FTPS SHA-256 certificate pins.

### Moonraker / Klipper

- HTTP/WebSocket adapter foundation;
- common printer state and guarded control contracts;
- dynamic discovery of `extruder`, `extruderN` and `heater_bed` thermal objects;
- sparse target preservation without guessing unsupported chamber telemetry.

### Queue, inventory and filament accounting

- durable SQLite-backed queue with retry/reconciliation boundaries;
- immutable staged-3MF inspection and selected-plate material requirements;
- explicit operator material bindings and fail-closed routing compilation;
- durable spool inventory with exact `Decimal` mass accounting;
- explicit physical-slot → FoxForge-spool assignments;
- Candidate 6 P3 accounting reconstructed on current architecture through R1–R5:
  - durable reservations and no overcommit;
  - idempotent planning and completed settlement;
  - fresh-routing pre-dispatch accounting guard before external side effects;
  - guarded runtime/API lifecycle and reconciliation;
  - operator accounting UI;
  - provider-scoped Candidate 6 validation gate.

Historical PR #58 is closed/unmerged and retained only as an archive/reference. P3 is integrated in current source, but it is not yet part of a published Candidate 6 or physical acceptance claim.

### Web interface

- React + TypeScript + Vite UI with EN/RU/UK localization;
- responsive phone, tablet, desktop and ultra-wide layouts;
- memory-only Operator Access credential handling;
- Material System UI 2.0 for AMS/external sources and toolhead routes;
- capability-driven Printer cards and Printer Detail views;
- staged Add Printer flow and secret-safe diagnostics;
- queue, spool inventory, accounting and common job-control workflows.

## Current support status

| Area | Status |
| --- | --- |
| Common printer architecture | Implemented |
| Bambu Lab adapter | Functional alpha; Candidate 6 physical validation not started |
| Bambu LAN discovery | Implemented foundation; real deployment-network validation pending |
| Moonraker/Klipper adapter | Functional alpha; physical OpenKE validation pending |
| Common thermal telemetry | Bambu + Moonraker implementations integrated |
| Fleet/reconnect supervision | Implemented foundation |
| Durable print queue | Implemented foundation |
| Pause / Resume / Cancel | Implemented; physical validation pending |
| Artifact staging | Implemented |
| Filament/spool inventory | Operator workflow implemented |
| Automatic filament accounting | P3 R1–R5 software integrated; publication/physical validation pending |
| AMS/CFS observation | Bambu AMS + external source foundation implemented |
| Persistent farm scheduler | Not implemented |
| Docker `amd64` / `arm64` | **C6-10 exact-main PASS**; Candidate 6 image not published |
| Umbrel | Candidate 5 remains installable; Candidate 6 package awaits C6-11 |

## Candidate 6 gate sequence

1. **C6-10 — PASS:** exact software source validated without publication side effects.
2. **C6-11 — next:** freeze exact source SHA, publish matching `linux/amd64` + `linux/arm64` image/digest and matching Umbrel package.
3. Run the real **Raspberry Pi 5 + Umbrel + X2D + AMS 2 Pro no-print gate** on that exact identity.
4. Only after complete no-print PASS, run one explicitly reviewed first-print path and guarded job control.
5. Any application-code change during physical Candidate 6 validation requires a new candidate; evidence cannot be carried across a changed digest.

## Installation

### Umbrel

FoxForge is available from the [MikeFox303 3D Printing Community App Store](https://github.com/MikeFox303/umbrel-3d-printing-store) as `my3d-foxforge`.

The Store currently serves the historical Candidate 5 package described above. Umbrel exposes the app password in its UI and maps `${APP_PASSWORD}` to `FOXFORGE_COMMAND_TOKEN`. Enter that value in **Operator Access / Unlock writes** when protected actions are required; the browser keeps the credential only in memory for the current tab.

See [Umbrel deployment](deployment/umbrel/README.md).

### Docker

The latest published semantic release image is:

```bash
docker pull ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.3
```

Standalone write-enabled deployments must configure a strong `FOXFORGE_COMMAND_TOKEN`; omitting it intentionally leaves protected commands disabled while reads remain available.

See [Docker deployment](deployment/docker/README.md). Back up the complete `/data` directory before upgrading between early-alpha builds.

## Architecture

FoxForge follows a ports-and-adapters design:

```text
                 Web UI / API / automation
                          |
                 application services
          +---------------+----------------+
          |               |                |
     FleetService    QueueService    InventoryService
          |               |
     PrinterAdapter + typed capabilities
          |
      +---+-------------------+
      |                       |
 BambuAdapter          MoonrakerAdapter
      |                       |
 MQTT / project          HTTP / WebSocket
 storage / discovery        transport
```

> **Normalize what is genuinely common; preserve what is genuinely vendor-specific.**

FoxForge studies **Bambuddy** for deep Bambu behavior, **PrintBuddy** for multi-vendor/provider isolation and **PrintOps** for farm/operations concepts. FoxForge owns its common contracts and application architecture. Any copied or derived upstream code must retain required copyright/license/provenance notices and be clearly distinguished from newly written FoxForge code.

Start with [ADR 0001](docs/adr/0001-printer-adapter-architecture.md) and the [documentation index](docs/README.md).

## Development

Backend:

```bash
git clone https://github.com/MikeFox303/FoxForge.git
cd FoxForge/backend
python -m venv .venv
# activate the environment
pip install -c constraints.txt -e ".[dev]"
pytest
ruff check src tests
ruff format --check src tests
```

Frontend:

```bash
cd ../frontend
npm ci
npm run check
npm test
npm run build
```

Repository guardrails are documented in [`AGENTS.md`](AGENTS.md).

## Documentation

- [Current project status](docs/project-status.md)
- [Candidate 6 software gate](docs/testing/pre-alpha-5-candidate6-software-gate.md)
- [Pre-Alpha 5 physical-validation history/runbook](docs/testing/pre-alpha-5-bambu-physical-validation.md)
- [Thermal telemetry](docs/design/thermal-telemetry.md)
- [Immutable 3MF print-plan inspection](docs/design/immutable-3mf-print-plan.md)
- [Material routing compiler](docs/design/material-routing-compiler.md)
- [Printer setup contract](docs/design/app-managed-printer-setup.md)
- [Reconnect supervision](docs/design/reconnect-supervision.md)
- [Bambu LAN transport](docs/design/bambu-lan-transport.md)
- [Moonraker transport](docs/design/moonraker-http-transport.md)
- [Release notes — v0.1.0-alpha.4.3](release/v0.1.0-alpha.4.3.md)

## Support FoxForge

FoxForge is free and open source. Voluntary support for development, test hardware and infrastructure is available through [Ko-fi](https://ko-fi.com/mikefox303). Support does not affect access to the project or its source code.

## License

FoxForge is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**. See [`LICENSE`](LICENSE).