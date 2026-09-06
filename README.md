# FoxForge

[![Release](https://img.shields.io/badge/pre--release-v0.1.0--alpha.4.3-orange)](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)
[![Alpha 5](https://img.shields.io/badge/Alpha%205-Candidate%205%20no--print%20gate-yellow)](docs/testing/pre-alpha-5-bambu-physical-validation.md)
[![License](https://img.shields.io/badge/license-AGPL--3.0--only-blue)](LICENSE)
[![Platforms](https://img.shields.io/badge/Linux-amd64%20%7C%20arm64-lightgrey)](deployment/README.md)

**FoxForge is an open-source, self-hosted platform for managing mixed fleets of 3D printers through a vendor-independent core while preserving deep vendor-specific capabilities.**

Bambu Lab is the current primary integration target. Moonraker/Klipper support remains part of the common architecture, while persistent farm scheduling and automatic filament accounting follow after the printer/deployment foundations are physically validated.

> [!WARNING]
> FoxForge is early alpha software. It is suitable for development and controlled self-hosted testing, but it is **not production-ready** and must not be represented as physically validated until the required real-device evidence is complete.

## Release and validation status

The latest published semantic pre-release is **[v0.1.0-alpha.4.3](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)**.

Development toward **`v0.1.0-alpha.5`** is tracked by [issue #115](https://github.com/MikeFox303/FoxForge/issues/115). The current immutable physical-validation target is **Candidate 5**:

```text
FoxForge application source: 0351c659f2d2845fb83bc0b1802c4d9ebeeef1f2
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.5
Umbrel Store commit: 16d57c486ce8e2b26abd5c7e9480188d95f080cb
exact image: ghcr.io/mikefox303/foxforge:sha-0351c65@sha256:00c699effbe9b245a4916a8c301df5b67435d75dd42fad02cc5bbf0ca51aec39
```

Candidate 5 replaces retired Candidate 4 and contains the routing-audit fix from PR #145: present-but-invalid 3MF toolhead metadata remains fail-closed, a fixed physical source route cannot mask corrupt slicer intent, and selected-plate readiness no longer lets an unrelated blocked plate poison a safe selected plate while global/selected blockers remain authoritative. It also includes the subsequent capability-driven UI refactor and staged Add Printer **Provider → Connection → Identity → Verify** flow merged through PR #150.

Candidate 5 has passed software/package gates and is now ready for the **no-print physical gate only**. Sections 1–6 of the physical-validation runbook must pass on the real Raspberry Pi 5 + Umbrel + X2D + AMS 2 Pro deployment before the first physical Start. Candidate 1/2/3/4 evidence must not be relabeled or silently carried to Candidate 5.

See the [Pre-Alpha 5 Bambu physical-validation runbook](docs/testing/pre-alpha-5-bambu-physical-validation.md).

## What current source provides

### Printer setup and fleet

- FoxForge-owned `PrinterAdapter` contracts with typed capability discovery;
- Bambu Lab LAN and Moonraker/Klipper adapters behind a vendor-neutral application boundary;
- application-managed Add / Update / Remove / Reconnect workflows;
- staged Add Printer **Provider → Connection → Identity → Verify** workflow with exact-payload verification invalidation before Save;
- test-before-save for Add and Update, so invalid reachability or credentials do not replace durable working configuration;
- rollback to the previous working adapter/configuration when a replacement connection fails;
- deterministic idempotent replay of terminal sanitized setup failures;
- conservative Bambu LAN discovery over bounded RFC1918 IPv4 subnets, including server-visible private subnet suggestions plus manual CIDR entry as fallback;
- restart-safe per-printer reconnect supervision with bounded backoff/jitter and secret-safe diagnostics.

### Bambu Lab depth

- MQTT/TLS live state transport;
- project-storage abstraction with FTPS implementation and fail-safe print-start semantics;
- normalized X2D/printer state foundation;
- AMS-family and external material-source observation through the common material-system capability;
- typed `foxforge.material_topology` routes with explicit fixed/dynamic/unknown toolhead reachability and stale-state handling;
- active source, remaining fraction, material identity and tag identity when reported by the printer;
- Bambu print dispatch defense that revalidates compiled source/toolhead routing and emits `ams_mapping`, `ams_mapping2` and `nozzle_mapping` only from proven intent;
- guarded common Pause / Resume / Cancel with exact active-job identity checks;
- optional independent MQTT and FTPS SHA-256 certificate pins.

Physical X2D/AMS 2 Pro validation is still required for the complete connection, storage, print-start, control and recovery matrix.

### Queue and inventory

- durable SQLite-backed queue with lifecycle, retry and reconciliation boundaries;
- immutable staged-3MF print-plan inspection with selected-plate logical requirements, explicit operator material bindings and fail-closed routing compilation;
- explicit distinction between missing toolhead metadata and present-but-invalid slicer/toolhead metadata;
- selected-plate routing semantics: an unrelated blocked plate does not poison a safe selected plate, while global/selected unsafe metadata remains blocking;
- compiler-owned toolhead bindings persisted before submit and revalidated again at dispatch;
- explicit `INDETERMINATE` handling instead of blind side-effect retry;
- content-addressed `.gcode` / `.3mf` staging with quota and safe garbage collection;
- durable spool inventory with exact `Decimal` accounting;
- create, edit empty-spool mass, correct mass, assign/move/unassign, archive and history workflows;
- opaque physical slot identifiers suitable for AMS/CFS/external material systems.

**Automatic filament consumption is not released.** The P3 implementation remains frozen until the physical/deployment gate is satisfied.

### Web interface and API

- React + TypeScript + Vite UI with EN/RU/UK localization;
- live FoxForge `/api/v1` read models and guarded command APIs;
- SSE application-event invalidation with canonical HTTP snapshots;
- responsive phone, tablet, desktop and ultra-wide layouts;
- Operator Access with a memory-only command credential;
- staged Add Printer workflow with discovery/manual fallback, safe subnet suggestions, structured setup errors and reconnect diagnostics;
- Printer Detail Material Topology UI with fixed/dynamic/unknown/stale presentation;
- capability-driven Printer Detail Control/Materials tabs instead of vendor/model feature inference;
- explicit selected-plate 3MF material-binding review plus queue, inventory and common job-control workflows.

## Current support status

| Area | Status |
| --- | --- |
| Common printer architecture | Implemented |
| Bambu Lab adapter | Functional alpha; Candidate 5 no-print physical validation pending |
| Bambu LAN discovery | Implemented foundation; real deployment-network validation pending |
| Moonraker/Klipper adapter | Functional alpha; physical OpenKE validation pending |
| Fleet/reconnect supervision | Implemented foundation |
| Durable print queue | Implemented foundation |
| Pause / Resume / Cancel | Implemented; physical validation pending |
| Artifact staging | Implemented |
| Filament/spool inventory | Normal operator workflow implemented |
| AMS/CFS observation | Bambu AMS/external observation foundation implemented |
| Deep AMS/CFS operations | Planned as typed vendor capabilities |
| Automatic filament accounting | Frozen / not released |
| Persistent farm scheduler | Not implemented |
| Docker `amd64` / `arm64` | Candidate 5 immutable image published and package-smoke-tested |
| Umbrel | Candidate 5 (`0.1.0-alpha.4.3-umbrel.5`) published; no-print physical gate pending |

## Installation

### Umbrel

FoxForge is available from the [MikeFox303 3D Printing Community App Store](https://github.com/MikeFox303/umbrel-3d-printing-store) as `my3d-foxforge`.

The current Pre-Alpha 5 validation package is **Candidate 5 (`0.1.0-alpha.4.3-umbrel.5`)**, pinned to the exact immutable image recorded above. It is the accepted target for new no-print Alpha 5 physical evidence. Candidate 4 is historical and must not be used for first-print acceptance.

Umbrel exposes the FoxForge app password in its UI and maps the same per-app password to `FOXFORGE_COMMAND_TOKEN`. Enter it in **Operator Access / Unlock writes** when protected actions are required. The browser keeps that credential only in memory for the current tab.

See [Umbrel deployment](deployment/umbrel/README.md).

### Docker

The latest published semantic release image is:

```bash
docker pull ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.3
```

Standalone write-enabled deployments must configure a strong `FOXFORGE_COMMAND_TOKEN`; omitting it intentionally leaves protected commands disabled while reads remain available.

See [Docker deployment](deployment/docker/README.md). Back up the complete `/data` directory before upgrading between early alpha builds.

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

FoxForge studies **Bambuddy** for deep Bambu behavior, **PrintBuddy** for multi-vendor/provider isolation and **PrintOps** for farm/operations concepts. FoxForge owns its common contracts and application architecture. Any copied or derived upstream code must retain required copyright/license notices and be clearly distinguished from newly written FoxForge code.

Start with [ADR 0001](docs/adr/0001-printer-adapter-architecture.md) and the [documentation index](docs/README.md).

## Repository layout

```text
FoxForge/
├── backend/       Python domain, adapters, services, API and runtime
├── frontend/      React / TypeScript / Vite web application
├── deployment/    Docker and Umbrel packaging
├── docs/          Architecture, design, testing, audit and project status
├── integrations/  Isolated migration/provenance material
└── release/       Immutable release identity and release notes
```

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

- [Documentation index](docs/README.md)
- [Current project status](docs/project-status.md)
- [Pre-Alpha 5 Bambu physical validation](docs/testing/pre-alpha-5-bambu-physical-validation.md)
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
