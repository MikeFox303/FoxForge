# FoxForge

[![Release](https://img.shields.io/badge/pre--release-v0.1.0--alpha.4.3-orange)](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)
[![License](https://img.shields.io/badge/license-AGPL--3.0--only-blue)](LICENSE)
[![Platforms](https://img.shields.io/badge/Linux-amd64%20%7C%20arm64-lightgrey)](deployment/README.md)

**FoxForge is an open-source, self-hosted platform for managing 3D printers through a vendor-independent core without reducing deep vendor-specific capabilities to a lowest-common-denominator interface.**

The project is being built for mixed printer fleets, with **Bambu Lab as the current primary integration target**, followed by Moonraker/Klipper and broader farm-management workflows.

> [!WARNING]
> FoxForge is early alpha software. The current release is suitable for development and controlled self-hosted testing, but it is **not production-ready**. Real-device validation of printer connectivity, job delivery and control is still in progress.

## Current release

The latest published pre-release is **[v0.1.0-alpha.4.3](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)**.

Alpha 4.3 is a browser compatibility hotfix for command flows on iOS Safari/WebKit when FoxForge is opened over a plain HTTP LAN address. It adds a cryptographically secure UUIDv4 fallback when `crypto.randomUUID()` is unavailable, restoring affected write operations such as printer setup, queue changes, inventory mutations and Pause/Resume/Cancel.

This hotfix does **not** change printer transports or persistence schemas. Existing Alpha 4.2 `/data` remains compatible.

Published container image:

```text
ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.3
```

The matching Umbrel Community App package is **`my3d-foxforge` `0.1.0-alpha.4.3`** and uses the same immutable Linux `amd64`/`arm64` image.

See the full [Alpha 4.3 release notes](release/v0.1.0-alpha.4.3.md).

## What FoxForge provides today

### Printer and fleet foundation

- FoxForge-owned `PrinterAdapter` abstraction with typed capabilities;
- Bambu Lab LAN integration foundation using MQTT/TLS and project-storage strategies;
- Moonraker/Klipper integration foundation using HTTP/WebSocket transport;
- normalized fleet state and per-printer reconnect supervision;
- common Pause, Resume and Cancel command model with exact job-identity checks;
- vendor-specific behavior kept behind typed capabilities instead of leaking into the common domain.

### Queue and print artifacts

- durable SQLite-backed print queue;
- lifecycle, retry and reconciliation foundations;
- explicit handling of ambiguous/indeterminate command outcomes;
- content-addressed `.gcode` and `.3mf` staging;
- quota, free-space reserve and safe artifact cleanup;
- authenticated and idempotent command APIs with audit records.

### Filament and spool inventory

- durable spool inventory;
- exact mass accounting using decimal values;
- create/edit/correct/archive workflows;
- spool assignment, move and unassign operations;
- inventory history;
- opaque physical slot identifiers suitable for AMS/CFS-style material systems.

**Automatic filament consumption is not included in Alpha 4.3.** It remains future work until physical printer/deployment validation is complete.

### Web interface

- React + TypeScript + Vite frontend;
- English, Russian and Ukrainian localization;
- responsive phone, tablet, desktop and ultra-wide layouts;
- printer setup, queue, inventory and common job-control flows;
- Server-Sent Events for realtime invalidation with canonical HTTP state snapshots;
- protected write operations through Operator Access.

### Deployment

- unified production container serving both the web UI and `/api/v1`;
- Linux `amd64` and `arm64` images;
- persistent application state under `/data`;
- Docker/Compose deployment;
- Umbrel Community App deployment;
- printer credentials separated from ordinary runtime configuration through `SecretStore`.

## Support status

| Area | Alpha 4.3 status |
| --- | --- |
| Common printer architecture | Implemented |
| Bambu Lab adapter | Alpha foundation implemented; physical X2D validation in progress |
| Moonraker/Klipper adapter | Alpha foundation implemented; physical validation pending |
| Fleet management | Implemented foundation |
| Durable print queue | Implemented foundation |
| Pause / Resume / Cancel | Implemented; physical validation pending |
| Artifact staging | Implemented |
| Filament/spool inventory | Implemented operator workflow |
| AMS/CFS depth | Partial foundation; deeper integration planned |
| Automatic filament accounting | Not released |
| Persistent farm scheduler | Not implemented yet |
| Docker `amd64` / `arm64` | Published |
| Umbrel | Alpha 4.3 package published |

## Installation

### Umbrel

FoxForge is available from the [MikeFox303 3D Printing Community App Store](https://github.com/MikeFox303/umbrel-3d-printing-store) as `my3d-foxforge`.

The Umbrel package maps its unique app password to `FOXFORGE_COMMAND_TOKEN`. Use the same app password in **Operator Access** when protected write operations need to be unlocked in the browser.

See [Umbrel deployment documentation](deployment/umbrel/README.md) for package and validation details.

### Docker

Docker and Compose deployment files are maintained under [`deployment/docker/`](deployment/docker/).

For the current release image:

```bash
docker pull ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.3
```

Standalone write-enabled deployments require a strong `FOXFORGE_COMMAND_TOKEN`. If the token is omitted, FoxForge remains readable while protected commands fail closed.

Back up the complete `/data` directory before upgrading between alpha releases.

## Architecture

FoxForge follows a ports-and-adapters design:

```text
                 Web UI / API / automation
                          |
                 Application services
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
 storage strategies          transport
```

The core rule is simple:

> **Normalize what is genuinely common; preserve what is genuinely vendor-specific.**

FoxForge studies existing open-source projects as specialized references:

- **Bambuddy** for deep Bambu protocol and product behavior;
- **PrintBuddy** for multi-vendor/provider isolation patterns;
- **PrintOps** for farm and operations concepts.

FoxForge owns its common contracts, application services, API/frontend boundaries, queue, inventory and deployment behavior. Copied or derived upstream code must retain the required copyright and license notices.

See [ADR 0001 — PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md), [ADR 0003 — upstream architecture synthesis](docs/adr/0003-upstream-architecture-synthesis.md) and the [upstream adoption map](docs/design/upstream-adoption-map.md).

## Repository layout

```text
FoxForge/
├── backend/       Python domain, adapters, services, API and runtime
├── frontend/      React / TypeScript / Vite web application
├── deployment/    Docker and Umbrel deployment material
├── docs/          Architecture, design, testing and project status
├── integrations/  Isolated migration/provenance material
└── release/       Release identity and release notes
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

Start with:

- [Documentation index](docs/README.md)
- [Project status](docs/project-status.md)
- [Physical validation runbook](docs/testing/physical-validation-runbook.md)
- [PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md)
- [Bambu LAN transport](docs/design/bambu-lan-transport.md)
- [Moonraker transport](docs/design/moonraker-http-transport.md)
- [Secret storage](docs/design/secret-storage.md)
- [Realtime application events](docs/design/realtime-events.md)
- [Release notes — v0.1.0-alpha.4.3](release/v0.1.0-alpha.4.3.md)

## Support FoxForge

FoxForge is free and open source. If you find the project useful and want to support continued development, test hardware and infrastructure, you can make a voluntary contribution on Ko-fi.

[☕ Support FoxForge on Ko-fi](https://ko-fi.com/mikefox303)

Support is optional and does not affect access to FoxForge or its source code.

## License

FoxForge is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.

See [`LICENSE`](LICENSE) for the full license text.
