# FoxForge

[![Release](https://img.shields.io/badge/pre--release-v0.1.0--alpha.4.3-orange)](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)
[![Alpha 5](https://img.shields.io/badge/Alpha%205-Candidate%207%20physical%20validation-yellow)](docs/project-status.md)
[![License](https://img.shields.io/badge/license-AGPL--3.0--only-blue)](LICENSE)
[![Platforms](https://img.shields.io/badge/Linux-amd64%20%7C%20arm64-lightgrey)](deployment/README.md)

**FoxForge is an open-source, self-hosted platform for managing mixed fleets of 3D printers through a vendor-independent core while preserving deep vendor-specific capabilities.**

Bambu Lab is the current primary integration target. Moonraker/Klipper is supported through the same common architecture, while material systems, queueing, filament accounting and future farm-management features remain capability-driven rather than tied to a single printer family.

> [!WARNING]
> FoxForge is early alpha software. It is suitable for development and controlled self-hosted testing, but it is **not production-ready**. CI, browser tests and QEMU/container smoke are not physical printer validation.

## Release and Candidate 7 status

The latest published semantic pre-release is **[v0.1.0-alpha.4.3](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)**. Final **`v0.1.0-alpha.5` has not been published**.

Pre-Alpha 5 is tracked by [#115](https://github.com/MikeFox303/FoxForge/issues/115), with replacement-candidate validation in [#154](https://github.com/MikeFox303/FoxForge/issues/154).

The current physical-validation target is **Candidate 7**:

```text
FoxForge application source: 4f769ca89d466d2cbe41360848b6343ec5a8eb36
image tag: ghcr.io/mikefox303/foxforge:sha-4f769ca
OCI digest: sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
exact image: ghcr.io/mikefox303/foxforge:sha-4f769ca@sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.7
Umbrel Store commit: 6e69e4005ae9529eeee5c376c8769393b056ee0d
```

The frozen Candidate 7 source passed the full exact-source software gate in run `34616523326`. Publication recovery run `34630673497` verified the immutable amd64/arm64 OCI index and independent anonymous pulls. Companion Store PR #39 passed package/runtime gates for both architectures and merged as Store commit `6e69e4005ae9529eeee5c376c8769393b056ee0d`.

Candidate history matters:

- Candidate 5 is historical after real X2D testing exposed partial `push_status` and dual-external `vir_slot` compatibility gaps;
- Candidate 6 is historical/failed after the real X2D could pass UI Verify and then fail during Add Printer with `internal_adapter_error`;
- PR #184 fixed that setup lifecycle by using one backend-authoritative live Add connection before persistence and short per-session Bambu MQTT client IDs;
- because application code changed after Candidate 6 publication, its physical evidence cannot be reused for Candidate 7.

Candidate 7 is now **installable and authorized for the Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro no-print gate**. It is not yet physically accepted, and no physical Start should occur until no-print sections 1–7 in the runbook pass.

See the [Candidate 7 physical-validation runbook](docs/testing/pre-alpha-5-bambu-physical-validation.md) and [current project status](docs/project-status.md).

## What current application source provides

### Printer setup and fleet

- FoxForge-owned `PrinterAdapter` contracts with typed capability discovery;
- Bambu Lab LAN and Moonraker/Klipper adapters behind vendor-neutral application boundaries;
- application-managed Add / Update / Remove / Reconnect workflows;
- staged Add Printer **Provider → Connection → Identity → Verify** with exact-payload verification invalidation before Save;
- Add uses the live fleet adapter as the single backend-authoritative connection before durable config/secrets are accepted;
- Update keeps a separate preflight and rollback path to protect an already-known-good printer;
- bounded Bambu LAN discovery with manual fallback;
- restart-safe reconnect supervision with bounded backoff/jitter and secret-safe diagnostics.

### Deep Bambu Lab support

- MQTT/TLS live-state transport with short per-session client IDs;
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
- P3 accounting reconstructed on current architecture through R1–R5:
  - durable reservations and no overcommit;
  - idempotent planning and completed settlement;
  - fresh-routing pre-dispatch accounting guard before external side effects;
  - guarded runtime/API lifecycle and reconciliation;
  - operator accounting UI;
  - provider-scoped Bambu validation gate.

Historical PR #58 is closed/unmerged and retained only as an archive/reference. Candidate 7's Umbrel package intentionally enables `bambu-validation`; Moonraker/Klipper automatic accounting remains outside that mode.

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
| Bambu Lab adapter | Functional alpha; Candidate 7 physical validation active |
| Bambu LAN discovery | Implemented foundation; real deployment-network validation pending |
| Bambu Add Printer | Candidate 7 Verify → Add real-device regression pending |
| Moonraker/Klipper adapter | Functional alpha; physical OpenKE validation pending |
| Common thermal telemetry | Bambu + Moonraker implementations integrated |
| Fleet/reconnect supervision | Implemented foundation |
| Durable print queue | Implemented foundation |
| Pause / Resume / Cancel | Implemented; physical validation pending |
| Artifact staging | Implemented |
| Filament/spool inventory | Operator workflow implemented |
| Automatic filament accounting | Bambu Candidate 7 validation mode published; physical acceptance pending |
| AMS/CFS observation | Bambu AMS + external source foundation implemented |
| Persistent farm scheduler | Not implemented |
| Docker `amd64` / `arm64` | Candidate 7 immutable multi-arch image published and anonymously verified |
| Umbrel | Candidate 7 `.7` package published and Store gates green |

## Candidate 7 gate sequence

1. **Publication — PASS:** exact application source, multi-architecture OCI digest and Umbrel `.7` package are frozen and published.
2. Run the real **Raspberry Pi 5 + Umbrel + X2D + AMS 2 Pro no-print gate** on that exact identity.
3. First prove the Candidate 6 blocker is gone: exact X2D payload **Verify → Add** must persist/connect without `internal_adapter_error`.
4. Complete Update rollback, restart/reconnect, network-loss diagnostics, partial status, thermal telemetry, AMS/external topology and accounting-mode checks.
5. Only after every no-print section passes, run one explicitly reviewed first-print/accounting path and guarded job control.
6. Any application/image/package-definition change after physical evidence begins requires Candidate 8; evidence cannot be carried across the changed identity.

## Installation

### Umbrel

FoxForge is available from the [MikeFox303 3D Printing Community App Store](https://github.com/MikeFox303/umbrel-3d-printing-store) as `my3d-foxforge`.

For the current Alpha 5 physical-validation track, refresh the Store and install/update to **`0.1.0-alpha.4.3-umbrel.7`**. The package pins the exact Candidate 7 image/digest shown above and enables Bambu-only `bambu-validation` accounting.

Umbrel exposes the app password in its UI and maps `${APP_PASSWORD}` to `FOXFORGE_COMMAND_TOKEN`. Enter that value in **Operator Access / Unlock writes** when protected actions are required; the browser keeps the credential only in memory for the current tab.

See [Umbrel deployment](deployment/umbrel/README.md).

### Docker

The latest published semantic release image remains:

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
- [Candidate 7 physical-validation runbook](docs/testing/pre-alpha-5-bambu-physical-validation.md)
- [Legacy Candidate 6 software gate / Candidate 7 exact-source gate](docs/testing/pre-alpha-5-candidate6-software-gate.md)
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
