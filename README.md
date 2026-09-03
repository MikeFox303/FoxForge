# FoxForge

**FoxForge is an open-source, self-hosted foundation for managing mixed fleets of 3D printers without sacrificing deep vendor-specific functionality.**

The project is building a common printer-management core for Bambu Lab, Moonraker/Klipper, print queues, material systems, inventory, and future farm-management workflows. FoxForge uses vendor-neutral contracts for genuinely common behavior while keeping advanced platform features available through typed vendor capabilities instead of reducing every printer to a lowest-common-denominator API.

> **Development status:** pre-alpha (`0.1.0.dev0`). FoxForge does not have a stable release or a complete end-user application yet. The core architecture and several printer/queue components are implemented and tested, while production hardware validation and higher-level application features are still in progress.

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

The common domain owns printer identity, normalized state, jobs, events, errors and capability discovery. Vendor protocol payloads and model-specific behavior stay behind their adapter boundaries.

See [ADR 0001: PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md) and the [printer contracts](docs/design/printer-contracts.md) for the normative design.

## Current implementation

The repository already contains more than design documents and experiments.

| Area | Current state |
| --- | --- |
| Common printer domain | Implemented with normalized identity, snapshots, events, errors and typed capabilities |
| PrinterAdapter contracts | Implemented with contract tests and architecture guards |
| Fleet management | `AdapterRegistry` and vendor-neutral `FleetService` implemented |
| Print queue | Durable vendor-neutral dispatch, normalized remote-job lifecycle tracking, and safe single-pass retry/backoff runner implemented |
| Queue persistence | SQLite store with restart-safe dispatch/idempotency and completed-lifecycle persistence implemented |
| Bambu adapter | Foundation, state mapping, print execution and material-system support implemented |
| Bambu LAN transport | MQTT/TLS + implicit-FTPS implementation; physical-printer validation pending |
| Bambu project storage | Bambu-specific storage strategy seam implemented; FTPS is default and future X2D/eMMC storage remains hardware-led work |
| Moonraker/Klipper adapter | Foundation, state mapping, print execution and external-spool semantics implemented |
| Moonraker transport | HTTP/WebSocket implementation and CI validation complete; physical-printer validation pending |

The queue deliberately persists `DISPATCHING` before invoking a printer side effect and treats uncertain starts as `INDETERMINATE`, preventing a process restart from blindly starting the same job twice. Confirmed jobs can then advance through `PREPARING`, `PRINTING`, `PAUSED`, `COMPLETED`, `FAILED` or `CANCELLED` from normalized fleet events when a stable `vendor_job_id` matches.

`QueueRunner` adds a deterministic one-pass scheduling primitive. It may retry only confirmed pre-start failures explicitly marked `retryable`, after exponential backoff and within an attempt limit. It never retries `DISPATCHING`, `INDETERMINATE`, or any receipt-bearing job, and it processes at most one candidate per printer in a pass.

## What is not finished yet

FoxForge should not currently be presented as a ready replacement for Bambuddy, Moonraker frontends, or a complete printer-farm application.

Work still includes:

- physical validation of Bambu LAN behavior, especially X2D/N6 storage and print-start paths;
- physical Moonraker/OpenKE validation;
- a persistent scheduler/timer and farm-level printer selection/priority policy above the single-pass queue runner;
- filament/spool inventory and reservation/consumption workflows;
- deeper Bambu-only capabilities such as AMS operations, drying, HMS, K profiles and dual-nozzle controls;
- persisted printer configuration and dynamic fleet management;
- public API and web UI;
- complete Docker/Umbrel deployment packaging;
- additional vendor adapters after the common contracts are proven.

See [`CHANGELOG.md`](CHANGELOG.md) for the latest implementation milestones and validation status.

## Bambu and upstream projects

FoxForge is its own project and is **not a Bambuddy distribution or permanent fork**.

Bambuddy, PrintBuddy and PrintOps were studied while defining the architecture. FoxForge keeps its multi-vendor core independent from those applications while documenting provenance where upstream behavior informed an implementation.

The remaining [`integrations/bambuddy/`](integrations/bambuddy/) content is limited to migration/provenance and localization records. The former X2D port-6000 experiment was deliberately removed rather than carried forward as dormant implementation code. Any future X2D/eMMC transport will be newly implemented behind `BambuProjectStorage` after physical validation.

Production Umbrel packaging of official Bambuddy releases remains a separate concern in `MikeFox303/umbrel-3d-printing-store`.

## Documentation

Durable architecture and implementation decisions live in [`docs/`](docs/README.md).

Key documents include:

- [ADR 0001: PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md)
- [Printer contracts v1](docs/design/printer-contracts.md)
- [Bambu adapter foundation](docs/design/bambu-adapter-foundation.md)
- [Bambu LAN production transport](docs/design/bambu-lan-transport.md)
- [Bambu project storage strategy](docs/design/bambu-project-storage.md)
- [AdapterRegistry and FleetService](docs/design/fleet-service.md)
- [Queue dispatch and durable idempotency](docs/design/queue-dispatch.md)
- [Queue event-driven print lifecycle](docs/design/queue-event-lifecycle.md)
- [Queue retry and single-pass runner policy](docs/design/queue-retry-policy.md)
- [Moonraker/Klipper adapter foundation](docs/design/moonraker-adapter-foundation.md)
- [Moonraker HTTP/WebSocket transport](docs/design/moonraker-http-transport.md)

## Development

FoxForge currently targets **Python 3.12+**.

```bash
git clone https://github.com/MikeFox303/FoxForge.git
cd FoxForge
python -m venv .venv

# Activate the virtual environment, then:
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

Implementation changes should respect the dependency boundaries defined by the ADR/design documents and include tests for new contracts, adapters and failure semantics.

## ❤️ Support FoxForge

FoxForge is free and open-source. If you find the project useful and would like to support continued development, test hardware and infrastructure, you can make a voluntary contribution on Ko-fi.

[☕ Support FoxForge on Ko-fi](https://ko-fi.com/mikefox303)

Support is completely optional and does not affect access to FoxForge or its source code.

## License

FoxForge is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.

See [`LICENSE`](LICENSE) for the full license text.
