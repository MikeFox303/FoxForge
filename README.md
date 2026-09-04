# FoxForge

**FoxForge is an open-source, self-hosted platform for managing mixed fleets of 3D printers without sacrificing deep vendor-specific functionality.**

FoxForge is building a common printer-management core for Bambu Lab, Moonraker/Klipper, print queues, material systems, filament inventory and farm-management workflows. Common behavior is exposed through vendor-neutral contracts, while advanced platform features remain available through typed vendor capabilities instead of being reduced to a lowest-common-denominator API.

> **Development status:** `0.1.0.dev0` — first runnable alpha candidate. FoxForge now ships a unified backend + web UI runtime with a versioned read API, SQLite persistence and Docker packaging. It is **not production-ready yet**: real printer command APIs, realtime delivery, physical hardware validation, automatic filament accounting, farm scheduling and Umbrel packaging remain active work.

## Current alpha capabilities

The current `main` branch includes:

- a FoxForge-owned `PrinterAdapter` architecture with typed capabilities;
- Bambu Lab and Moonraker/Klipper adapters behind the same common application boundary;
- `FleetService` and adapter registry composition;
- a durable SQLite-backed print queue with explicit `INDETERMINATE` handling and safe retry/backoff rules;
- a durable SQLite filament/spool inventory with exact `Decimal` mass accounting, immutable idempotent adjustments and opaque physical-slot assignments;
- a versioned read-only HTTP API at `/api/v1` for fleet, queue and inventory state;
- a React + TypeScript + Vite web interface connected to the live `/api/v1` read models in normal runtime mode;
- explicit demo data only when requested with `?demo=1`;
- English, Russian and Ukrainian interface localization (`en`, `ru`, `uk`) with translation parity tests;
- one `aiohttp` server process serving both the compiled SPA and the backend API;
- a multi-stage Docker image and standalone Compose configuration;
- persistent `/data/config.json` and `foxforge.sqlite3` state;
- non-root steady-state container execution;
- CI coverage for Python 3.12/3.13, frontend type/tests/build and container startup smoke tests;
- multi-architecture image publication preparation for Linux `amd64` and `arm64`.

## Project goals

FoxForge is intended to become a self-hosted 3D-printer management platform with:

- multi-vendor printer management behind a common `PrinterAdapter` boundary;
- deep Bambu Lab support rather than a simplified compatibility layer;
- Moonraker/Klipper support for compatible printers;
- AMS/CFS/external-spool material-system integration;
- filament and spool inventory with automated consumption tracking;
- durable print queues and multi-printer/farm workflows;
- server-side operation suitable for Docker, ARM64 and Umbrel;
- APIs and a user interface built above the same vendor-independent application layer.

Bambu-specific capabilities such as AMS-family operations, drying, HMS, K profiles, dual-nozzle control, Virtual Printer and future X2D-specific storage/transport can remain first-class Bambu capabilities without leaking Bambu concepts into Moonraker or other adapters.

## Repository layout

```text
FoxForge/
├── backend/       Python 3.12+ domain, adapters, services, API and runtime
├── frontend/      TypeScript/React/Vite web application
├── deployment/    Docker runtime and future Umbrel packaging
├── docs/          ADRs, design specifications and project status
└── integrations/  isolated migration/provenance material
```

The layout is governed by [ADR 0002: Repository layout](docs/adr/0002-repository-layout.md). Backend, frontend and deployment remain independently testable ownership areas but ship as one FoxForge application.

## Architecture

FoxForge follows a ports-and-adapters design.

```text
              Web UI / API / automation
                       |
              application services
          /-------------+-------------\
   FleetService    QueueService   InventoryService
          \             |             /
        PrinterAdapter + typed capabilities
                       |
              +--------+---------+
              |                  |
         BambuAdapter      MoonrakerAdapter
              |                  |
       MQTT / project        HTTP / WebSocket
      storage strategies       transport
```

The governing rule is:

> **Normalize what is genuinely common; preserve what is genuinely vendor-specific.**

The common printer domain owns printer identity, normalized snapshots/events/errors and capability discovery. Inventory remains a separate vendor-independent bounded context. Vendor payloads and model-specific behavior stay behind their adapter boundaries. Runtime-only vendor imports are restricted to the composition root.

See [ADR 0001: PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md) and [Printer contracts v1](docs/design/printer-contracts.md).

## Runtime model

The first alpha runtime composes configured Bambu LAN and Moonraker printers from versioned local configuration. On first start it creates a safe empty `/data/config.json`. Printer connection failures do not bring down the web/API process; reconnect attempts continue in the background.

The same runtime owns queue and inventory persistence in the application SQLite database and serves:

- `/healthz` — process health;
- `/api/v1/fleet` — normalized fleet snapshots;
- `/api/v1/queue` — canonical queue lifecycle read model;
- `/api/v1/inventory/spools` — spool inventory read model;
- the compiled React SPA from the same server process.

The public API is intentionally read-only at this stage. No anonymous printer-control or inventory-mutation HTTP API has been introduced.

## Current implementation status

| Area | Current state |
| --- | --- |
| Common printer domain | Implemented with normalized identity, snapshots, events, errors and typed capabilities |
| Printer adapters | Bambu and Moonraker foundations implemented behind common contracts |
| Fleet management | `AdapterRegistry` and `FleetService` implemented |
| Print queue | Durable dispatch/lifecycle/retry foundation implemented with SQLite persistence |
| Filament inventory | Durable SQLite spool inventory with exact mass ledger and slot assignments implemented |
| Public API | Versioned read-only `/api/v1` implemented for fleet, queue and inventory |
| Web UI | Live read integration implemented; EN/RU/UK localized; write controls remain unavailable until command APIs exist |
| Bambu LAN transport | MQTT/TLS + implicit FTPS implementation; physical X2D/Bambu validation pending |
| Moonraker transport | HTTP/WebSocket implementation; physical OpenKE/Moonraker validation pending |
| Docker | Unified image + Compose implemented and startup-smoke-tested on CI |
| ARM64 | Image publication path prepared; release-grade ARM64 runtime validation remains pending |
| Umbrel | Packaging boundary defined; actual FoxForge Umbrel app still pending |
| Farm scheduler | Single-pass queue runner exists; persistent farm policy/scheduler is not implemented yet |

## What is not finished yet

FoxForge should not yet be presented as a production replacement for Bambuddy, Moonraker frontends or a complete printer-farm application.

Priority remaining work includes:

1. **Physical printer validation** for Bambu LAN/X2D and Moonraker/OpenKE: connect, live state, upload, print start, lifecycle and completion.
2. **Authenticated command APIs** for queue operations, printer commands and inventory mutations with validation, idempotency and normalized errors.
3. **Realtime delivery** through WebSocket/SSE into the frontend query cache.
4. **Automatic filament accounting** linked to print completion, material selection and trustworthy usage estimates.
5. **Farm scheduling** above `QueueRunner.run_once()`: printer selection, priority/deadline policy and durable multi-process lease/CAS semantics.
6. **Deep Bambu capabilities** including AMS operations/drying, HMS, K profiles, dual nozzle and Virtual Printer/X2D-specific behavior.
7. **Release-grade Docker/ARM64 validation and Umbrel packaging** using the same FoxForge runtime rather than a divergent fork.
8. Additional vendor adapters only after the common contracts are proven by real hardware use.

## Safety invariants

Several rules are deliberate and should remain true as the project grows:

- ambiguous print starts become `INDETERMINATE` and are never blindly retried;
- receipt-bearing jobs are never redispatched by retry logic;
- printer material snapshots expose physical state and opaque slot IDs, not FoxForge `spool_id` values;
- API DTOs and the frontend do not consume raw Bambu/Moonraker protocol payloads;
- runtime secrets stay in local configuration and are not exposed by public read DTOs;
- Docker and Umbrel must package the same application behavior;
- upstream-derived material must retain required copyright/license provenance and remain distinguishable from newly written FoxForge code.

## Bambu and upstream projects

FoxForge is its own project and is **not a Bambuddy distribution or permanent fork**.

Bambuddy, PrintBuddy and PrintOps were studied while defining architecture and interface workflows. FoxForge keeps its multi-vendor core and newly written UI independent while documenting provenance where upstream behavior or product patterns informed implementation.

The remaining [`integrations/bambuddy/`](integrations/bambuddy/) content is limited to migration/provenance and localization records. The retired X2D port-6000 experiment was removed instead of being carried forward as dormant implementation code. Any future X2D/eMMC transport will be implemented behind `BambuProjectStorage` after physical validation.

Production Umbrel packaging of official Bambuddy releases remains a separate concern in `MikeFox303/umbrel-3d-printing-store`.

## Documentation

Durable architecture and implementation decisions live in [`docs/`](docs/README.md).

Key documents include:

- [Current project status](docs/project-status.md)
- [ADR 0001: PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md)
- [ADR 0002: Repository layout](docs/adr/0002-repository-layout.md)
- [Printer contracts v1](docs/design/printer-contracts.md)
- [Bambu LAN production transport](docs/design/bambu-lan-transport.md)
- [Bambu project storage strategy](docs/design/bambu-project-storage.md)
- [Moonraker HTTP/WebSocket transport](docs/design/moonraker-http-transport.md)
- [Queue dispatch and durable idempotency](docs/design/queue-dispatch.md)
- [Queue event-driven lifecycle](docs/design/queue-event-lifecycle.md)
- [Queue retry policy](docs/design/queue-retry-policy.md)
- [Inventory foundation](docs/design/inventory-foundation.md)
- [SQLite inventory persistence](docs/design/inventory-sqlite.md)
- [Public API v1](docs/design/public-api-v1.md)
- [Web UI foundation](docs/design/web-ui-foundation.md)
- [Frontend parallel development policy](docs/design/frontend-parallel-development.md)

See [`CHANGELOG.md`](CHANGELOG.md) for implementation and validation history.

## Development

Backend development targets **Python 3.12+**.

```bash
git clone https://github.com/MikeFox303/FoxForge.git
cd FoxForge/backend
python -m venv .venv

# Activate the environment, then:
pip install -e ".[dev]"
pytest
ruff check src tests
ruff format --check src tests
```

For the web UI:

```bash
cd ../frontend
npm install
npm run dev

npm run check
npm test
npm run build
```

For the current standalone container/Compose runtime, see [`deployment/docker/`](deployment/docker/).

Frontend and backend development may proceed in parallel, but merged `main` is the authoritative contract state. Implementation changes should respect the ADR/design boundaries and include acceptance criteria plus tests for new contracts and failure semantics.

## ❤️ Support FoxForge

FoxForge is free and open-source. If you find the project useful and would like to support continued development, test hardware and infrastructure, you can make a voluntary contribution on Ko-fi.

[☕ Support FoxForge on Ko-fi](https://ko-fi.com/mikefox303)

Support is completely optional and does not affect access to FoxForge or its source code.

## License

FoxForge is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.

See [`LICENSE`](LICENSE) for the full license text.
