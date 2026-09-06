# FoxForge

[![Release](https://img.shields.io/badge/pre--release-v0.1.0--alpha.4.3-orange)](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)
[![Alpha 5](https://img.shields.io/badge/Alpha%205-physical%20validation-yellow)](docs/testing/pre-alpha-5-bambu-physical-validation.md)
[![License](https://img.shields.io/badge/license-AGPL--3.0--only-blue)](LICENSE)
[![Platforms](https://img.shields.io/badge/Linux-amd64%20%7C%20arm64-lightgrey)](deployment/README.md)

**FoxForge is an open-source, self-hosted platform for managing mixed fleets of 3D printers through a vendor-independent core while preserving deep vendor-specific capabilities.**

Bambu Lab is the current primary integration target. Moonraker/Klipper support remains part of the common architecture, while persistent farm scheduling and automatic filament accounting follow after the printer/deployment foundations are physically validated.

> [!WARNING]
> FoxForge is early alpha software. It is suitable for development and controlled self-hosted testing, but it is **not production-ready** and must not be represented as physically validated until the required real-device evidence is complete.

## Release and validation status

The latest published semantic pre-release is **[v0.1.0-alpha.4.3](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)**.

Development toward **`v0.1.0-alpha.5`** is currently in physical-validation stage under [issue #115](https://github.com/MikeFox303/FoxForge/issues/115). The companion Umbrel Store currently carries validation candidate **`0.1.0-alpha.4.3-umbrel.2`**, built from FoxForge commit `37b253f385c19451c7ea075a4a4d12378cf17cf2` and pinned to:

```text
ghcr.io/mikefox303/foxforge:sha-37b253f@sha256:e550c8026ed6ec80e973d91fe6d96cc1474d537ca87de7875ec54f4a03aaaa4f
```

This package is deliberately **not** a final Alpha 5 release. Evidence collected against another image or package must not be relabeled as Alpha 5 evidence.

See the [Pre-Alpha 5 Bambu physical-validation runbook](docs/testing/pre-alpha-5-bambu-physical-validation.md).

## What current source provides

### Printer setup and fleet

- FoxForge-owned `PrinterAdapter` contracts with typed capability discovery;
- Bambu Lab LAN and Moonraker/Klipper adapters behind a vendor-neutral application boundary;
- application-managed Add / Update / Remove / Reconnect workflows;
- test-before-save for Add and Update, so invalid reachability or credentials do not replace durable working configuration;
- rollback to the previous working adapter/configuration when a replacement connection fails;
- deterministic idempotent replay of terminal sanitized setup failures;
- conservative Bambu LAN discovery over an explicitly selected RFC1918 IPv4 subnet, with manual entry retained as fallback;
- restart-safe per-printer reconnect supervision with bounded backoff/jitter and secret-safe diagnostics.

### Bambu Lab depth

- MQTT/TLS live state transport;
- project-storage abstraction with FTPS implementation and fail-safe print-start semantics;
- normalized X2D/printer state foundation;
- AMS-family and external material-source observation through the common material-system capability;
- active source, remaining fraction, material identity and tag identity when reported by the printer;
- guarded common Pause / Resume / Cancel with exact active-job identity checks;
- optional independent MQTT and FTPS SHA-256 certificate pins.

Physical X2D/AMS 2 Pro validation is still required for the complete connection, storage, print-start, control and recovery matrix.

### Queue and inventory

- durable SQLite-backed queue with lifecycle, retry and reconciliation boundaries;
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
- Add Printer discovery/manual flow, structured setup errors and reconnect diagnostics;
- queue, inventory and common job-control workflows.

## Current support status

| Area | Status |
| --- | --- |
| Common printer architecture | Implemented |
| Bambu Lab adapter | Functional alpha; real X2D/AMS acceptance in progress |
| Bambu LAN discovery | Implemented foundation; real deployment-network validation in progress |
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
| Docker `amd64` / `arm64` | Published alpha foundation |
| Umbrel | Pre-Alpha 5 validation candidate 2 published |

## Installation

### Umbrel

FoxForge is available from the [MikeFox303 3D Printing Community App Store](https://github.com/MikeFox303/umbrel-3d-printing-store) as `my3d-foxforge`.

The current Store package is a **Pre-Alpha 5 validation candidate**. Umbrel exposes the app password in its UI and maps the same per-app password to `FOXFORGE_COMMAND_TOKEN`. Enter it in **Operator Access / Unlock writes** when protected actions are required. The browser keeps that credential only in memory for the current tab.

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
- [Printer setup contract](docs/design/app-managed-printer-setup.md)
- [Reconnect supervision](docs/design/reconnect-supervision.md)
- [Bambu LAN transport](docs/design/bambu-lan-transport.md)
- [Moonraker transport](docs/design/moonraker-http-transport.md)
- [Release notes — v0.1.0-alpha.4.3](release/v0.1.0-alpha.4.3.md)

## Support FoxForge

FoxForge is free and open source. Voluntary support for development, test hardware and infrastructure is available through [Ko-fi](https://ko-fi.com/mikefox303). Support does not affect access to the project or its source code.

## License

FoxForge is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**. See [`LICENSE`](LICENSE).
