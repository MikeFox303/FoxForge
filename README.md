# FoxForge

**FoxForge is an open-source, self-hosted foundation for managing mixed fleets of 3D printers without sacrificing deep vendor-specific functionality.**

The project is building a common printer-management core for Bambu Lab, Moonraker/Klipper, print queues, material systems, inventory, and future farm-management workflows. FoxForge uses vendor-neutral contracts for genuinely common behavior while keeping advanced platform features available through typed vendor capabilities instead of reducing every printer to a lowest-common-denominator API.

> **Development status:** pre-alpha (`0.1.0.dev0`). FoxForge does not have a stable release or a complete end-user application yet. The core architecture, printer adapters, queue lifecycle, inventory foundation and a runnable web-UI foundation are implemented and tested. Live API integration, production hardware validation and higher-level application features are still in progress.

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

Bambu-specific capabilities such as AMS-family behavior, drying, HMS, K profiles, dual-nozzle control, Virtual Printer and future X2D-specific transport can remain first-class Bambu features without leaking Bambu concepts into Moonraker or other adapters.

## Repository layout

FoxForge separates its implementation into explicit top-level areas:

```text
FoxForge/
├── backend/       Python 3.12+ core, adapters, queue, inventory, persistence and future REST/WebSocket API
├── frontend/      TypeScript/React/Vite web application
├── deployment/    Docker and Umbrel packaging
├── docs/          ADRs and durable design specifications
└── integrations/  isolated upstream migration/provenance material
```

The layout is governed by [ADR 0002: Repository layout](docs/adr/0002-repository-layout.md). Backend, frontend and deployment remain independently testable but ship as one FoxForge application.

## Architecture

FoxForge follows a ports-and-adapters design.

```text
        API / UI / automation
                 |
        application services
       /                    \
 FleetService            QueueService
       \                    /
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

The common domain owns printer identity, normalized state, jobs, events, errors and capability discovery. Inventory is a separate vendor-independent bounded context. Vendor protocol payloads and model-specific behavior stay behind their adapter boundaries.

See [ADR 0001: PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md) and the [printer contracts](docs/design/printer-contracts.md) for the normative printer design.

## Current implementation

The repository already contains more than design documents and experiments.

| Area | Current state |
| --- | --- |
| Common printer domain | Implemented with normalized identity, snapshots, events, errors and typed capabilities |
| PrinterAdapter contracts | Implemented with contract tests and architecture guards |
| Fleet management | `AdapterRegistry` and vendor-neutral `FleetService` implemented |
| Print queue | Durable vendor-neutral dispatch, normalized remote-job lifecycle tracking, and safe single-pass retry/backoff runner implemented |
| Queue persistence | SQLite store with restart-safe dispatch/idempotency and completed-lifecycle persistence implemented |
| Filament inventory | Independent spool domain/application foundation with immutable idempotent mass adjustments and opaque printer/slot assignments implemented |
| Bambu adapter | Foundation, state mapping, print execution and material-system support implemented |
| Bambu LAN transport | MQTT/TLS + implicit-FTPS implementation; physical-printer validation pending |
| Bambu project storage | Bambu-specific storage strategy seam implemented; FTPS is default and future X2D/eMMC storage remains hardware-led work |
| Moonraker/Klipper adapter | Foundation, state mapping, print execution and external-spool semantics implemented |
| Moonraker transport | HTTP/WebSocket implementation and CI validation complete; physical-printer validation pending |
| Web UI foundation | React/TypeScript/Vite interface with React Router, TanStack Query, i18next, printer cockpit, queue/material/farm views and responsive layout; public API/realtime wiring pending |

The queue deliberately persists `DISPATCHING` before invoking a printer side effect and treats uncertain starts as `INDETERMINATE`, preventing a process restart from blindly starting the same job twice. Confirmed jobs can then advance through `PREPARING`, `PRINTING`, `PAUSED`, `COMPLETED`, `FAILED` or `CANCELLED` from normalized fleet events when a stable `vendor_job_id` matches.

`QueueRunner` adds a deterministic one-pass scheduling primitive. It may retry only confirmed pre-start failures explicitly marked `retryable`, after exponential backoff and within an attempt limit. It never retries `DISPATCHING`, `INDETERMINATE`, or any receipt-bearing job, and it processes at most one candidate per printer in a pass.

## What is not finished yet

FoxForge should not currently be presented as a ready replacement for Bambuddy, Moonraker frontends, or a complete printer-farm application.

Work still includes:

- physical validation of Bambu LAN behavior, especially X2D/N6 storage and print-start paths;
- physical Moonraker/OpenKE validation;
- a persistent scheduler/timer and farm-level printer selection/priority policy above the single-pass queue runner;
- inventory persistence plus automated reservation/consumption integration with completed print jobs and material systems;
- deeper Bambu-only capabilities such as AMS operations, drying, HMS, K profiles and dual-nozzle controls;
- persisted printer configuration and dynamic fleet management;
- public REST/WebSocket API and live web-UI integration replacing the current demo gateway;
- production Docker/Umbrel deployment packaging;
- additional vendor adapters after the common contracts are proven.

See [`CHANGELOG.md`](CHANGELOG.md) for the latest implementation milestones and validation status.

## Bambu and upstream projects

FoxForge is its own project and is **not a Bambuddy distribution or permanent fork**.

Bambuddy, PrintBuddy and PrintOps were studied while defining the architecture and interface workflows. FoxForge keeps its multi-vendor core and newly written UI independent from those applications while documenting provenance where upstream behavior or product patterns informed an implementation.

The remaining [`integrations/bambuddy/`](integrations/bambuddy/) content is limited to migration/provenance and localization records. The former X2D port-6000 experiment was deliberately removed rather than carried forward as dormant implementation code. Any future X2D/eMMC transport will be newly implemented behind `BambuProjectStorage` after physical validation.

Production Umbrel packaging of official Bambuddy releases remains a separate concern in `MikeFox303/umbrel-3d-printing-store`.

## Documentation

Durable architecture and implementation decisions live in [`docs/`](docs/README.md).

Key documents include:

- [ADR 0001: PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md)
- [ADR 0002: Repository layout](docs/adr/0002-repository-layout.md)
- [Printer contracts v1](docs/design/printer-contracts.md)
- [Bambu adapter foundation](docs/design/bambu-adapter-foundation.md)
- [Bambu LAN production transport](docs/design/bambu-lan-transport.md)
- [Bambu project storage strategy](docs/design/bambu-project-storage.md)
- [AdapterRegistry and FleetService](docs/design/fleet-service.md)
- [Queue dispatch and durable idempotency](docs/design/queue-dispatch.md)
- [Queue event-driven print lifecycle](docs/design/queue-event-lifecycle.md)
- [Queue retry and single-pass runner policy](docs/design/queue-retry-policy.md)
- [Filament inventory foundation](docs/design/inventory-foundation.md)
- [Moonraker/Klipper adapter foundation](docs/design/moonraker-adapter-foundation.md)
- [Moonraker HTTP/WebSocket transport](docs/design/moonraker-http-transport.md)
- [Web UI foundation](docs/design/web-ui-foundation.md)

## Development

FoxForge backend currently targets **Python 3.12+**.

```bash
git clone https://github.com/MikeFox303/FoxForge.git
cd FoxForge/backend
python -m venv .venv

# Activate the virtual environment, then:
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

# Validation:
npm run check
npm test
npm run build
```

The production frontend builds to static assets; deployment packaging lives under `deployment/`.

Implementation changes should respect the dependency boundaries defined by the ADR/design documents and include tests for new contracts, adapters and failure semantics.

## ❤️ Support FoxForge

FoxForge is free and open-source. If you find the project useful and would like to support continued development, test hardware and infrastructure, you can make a voluntary contribution on Ko-fi.

[☕ Support FoxForge on Ko-fi](https://ko-fi.com/mikefox303)

Support is completely optional and does not affect access to FoxForge or its source code.

## License

FoxForge is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.

See [`LICENSE`](LICENSE) for the full license text.
