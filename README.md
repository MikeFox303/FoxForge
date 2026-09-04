# FoxForge

**FoxForge is an open-source, self-hosted platform for managing mixed fleets of 3D printers without sacrificing deep vendor-specific functionality.**

FoxForge combines a vendor-independent printer/application core with deep Bambu Lab support, Moonraker/Klipper support, durable print queues, filament/spool inventory, material-system integration, farm workflows and Docker/Umbrel deployment.

> **Published release:** `v0.1.0-alpha.3`  
> **Current source state:** `main` matches the `alpha.3` functional release line. Alpha.3 includes authenticated printer configuration, inventory mutations, audited queue command APIs, restart-safe artifact staging and the browser queue upload/enqueue/dispatch/reconciliation workflow. No post-`alpha.3` functional changes are recorded yet.  
> **Maturity:** runnable/installable alpha, **not production-ready**. Physical Bambu X2D, Moonraker/OpenKE and representative Raspberry Pi/Umbrel validation are still required.

## What FoxForge currently implements

The current source tree includes:

- FoxForge-owned `PrinterAdapter` contracts with typed capability discovery;
- Bambu Lab and Moonraker/Klipper adapters behind the same common application boundary;
- `FleetService` and dynamic adapter composition;
- Bambu LAN MQTT/TLS + verified project storage/FTPS foundations;
- Moonraker HTTP/WebSocket transport with upload/start support;
- a durable SQLite print queue with explicit `INDETERMINATE` handling, lifecycle tracking and safe retry/backoff;
- restart-safe content-addressed `.gcode`/`.3mf` artifact staging under `/data/artifacts`;
- authenticated/idempotent queue enqueue, dispatch and explicit reconciliation commands;
- a durable SQLite filament/spool inventory with exact `Decimal` accounting and opaque physical-slot assignments;
- authenticated inventory mutations for create/correct/empty-mass/move/unassign/archive;
- authenticated printer configuration flows for add/update/remove/test/reconnect;
- append-only SQLite command audit and durable HTTP idempotency records;
- a React + TypeScript + Vite interface using live FoxForge API models;
- browser operator-session support for guarded write workflows;
- printer setup UI plus a safe print workflow that hashes files in the browser and never sends client filesystem paths;
- EN/RU/UK localization with translation-parity tests;
- one `aiohttp` runtime serving API + compiled SPA;
- Docker, Linux `amd64`/`arm64`, Compose and Umbrel packaging foundations;
- CI for Python 3.12/3.13, frontend type/tests/build and unified-container smoke validation.

The shipped `v0.1.0-alpha.3` image is immutable. Future `main` changes require a later guarded release before Docker/Umbrel users receive them.

## Core architecture

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
 storage strategies          transport
```

The governing rule is:

> **Normalize what is genuinely common; preserve what is genuinely vendor-specific.**

Common application/domain code must not import Bambu or Moonraker transport types. Deep Bambu features remain first-class typed Bambu capabilities instead of being flattened into a lowest-common-denominator interface.

FoxForge uses upstream projects as specialized references:

- **Bambuddy** — primary Bambu protocol/product-behavior reference;
- **PrintBuddy** — multi-vendor/provider-isolation reference;
- **PrintOps** — farm/operations/scheduling reference;
- **FoxForge** — owner of the common contracts, API/frontend boundaries, queue, inventory and deployment behavior.

See [ADR 0001](docs/adr/0001-printer-adapter-architecture.md), [ADR 0003](docs/adr/0003-upstream-architecture-synthesis.md) and the [Upstream adoption map](docs/design/upstream-adoption-map.md).

## Safe command model

Remote writes follow [ADR 0004](docs/adr/0004-command-api-security.md):

- fail-closed authentication;
- explicit command permissions;
- request correlation IDs;
- durable `Idempotency-Key` semantics;
- normalized errors;
- append-only command audit;
- no blind replay of uncertain printer side effects.

For print submission the released alpha.3 flow is:

```text
browser File
   |
SHA-256 in browser
   |
POST /api/v1/artifacts   (bytes only, no local path)
   |
verified content-addressed artifact
   |
POST /api/v1/queue
   |
durable queue entry + dispatch_id
   |
POST /api/v1/queue/{id}/dispatch
   |
accepted | blocked | failed | INDETERMINATE
                              |
                    explicit reconciliation only
```

Important distinction:

- `dispatch_id` is the durable logical printer-dispatch identity owned by the queue;
- HTTP `Idempotency-Key` identifies one remote command attempt;
- an uncertain HTTP replay keeps the same key;
- a completed `BLOCKED` or explicitly retryable pre-start failure may later use a **new** HTTP key while preserving the queue's original `dispatch_id`;
- `INDETERMINATE` never exposes blind retry.

See [Queue command API and artifact staging](docs/design/queue-command-api.md).

## Web interface

The UI uses React, TypeScript, Vite, React Router, TanStack Query and i18next.

Current released behavior includes:

- live fleet, queue and inventory reads;
- explicit loading/refresh/error states;
- printer setup launcher and authenticated configuration dialog;
- queue file selection for `.gcode`/`.3mf`;
- SHA-256 hashing in the browser;
- staged upload, durable enqueue and separate explicit start command;
- retry controls only for backend-confirmed safe pre-start failures;
- explicit started/not-started reconciliation for `INDETERMINATE` queue entries;
- demo data only with `?demo=1`.

The checked-in screenshots under [`docs/images/ui/`](docs/images/ui/) are real captures from repository builds. Some screenshots document earlier alpha UI states and may not show every alpha.3 command control yet.

## Runtime and persistence

The unified server owns:

- `/healthz`;
- `/api/v1/fleet`;
- `/api/v1/queue`;
- `/api/v1/inventory/spools`;
- authenticated printer/inventory/queue command routes;
- browser operator-session bootstrap;
- the compiled React SPA.

Persistent `/data` includes:

- `config.json`;
- `foxforge.sqlite3`;
- staged print artifacts under `/data/artifacts`.

Printer connection failures do not bring down the web/API process. Reconnect supervision continues in the background.

## Current status matrix

| Area | Current source state |
| --- | --- |
| Common printer domain | Implemented |
| Bambu adapter | Foundation + LAN transport implemented; physical X2D validation pending |
| Moonraker adapter | Foundation + HTTP/WebSocket transport implemented; physical OpenKE validation pending |
| Fleet management | Implemented |
| Durable queue | Implemented foundation with lifecycle/retry/reconciliation |
| Artifact staging | Released in `alpha.3` |
| Queue command API | Released in `alpha.3` |
| Queue command UI | Released in `alpha.3`; automated frontend/container validation passed, physical printer validation still required |
| Filament inventory | Durable SQLite foundation implemented |
| Inventory command API | Released in `alpha.3` |
| Printer configuration API/UI | Released in `alpha.3` |
| Command auth/idempotency/audit | Released foundation in `alpha.3` |
| Realtime WebSocket/SSE | Not implemented |
| Automatic filament accounting | Not implemented |
| Persistent farm scheduler | Not implemented |
| Docker | Implemented and CI-smoke-tested |
| ARM64 | Published `alpha.3` multi-architecture image exists; representative Raspberry Pi validation pending |
| Umbrel | Community App is pinned to the immutable `alpha.3` multi-architecture digest |

## Hardware validation still required

FoxForge must not yet claim production-ready printer support.

Required real-device validation includes:

1. **Bambu X2D / Bambu LAN** — connection/reconnect, live state, project delivery, print start acknowledgement, lifecycle, completion and ambiguous-start reconciliation.
2. **Moonraker/OpenKE** — HTTP/WebSocket connectivity, live subscriptions, G-code upload/checksum/start and lifecycle completion/failure.
3. **Raspberry Pi 5 / UmbrelOS** — install/restart/persistence, explicit-IP reachability to printers and upgrade behavior.

Automated tests and QEMU/CI are necessary but do not replace these physical matrices.

## Next development priorities

1. Run documented physical Bambu X2D and Moonraker/OpenKE print-validation matrices using the released browser print workflow.
2. Validate Raspberry Pi 5/UmbrelOS install, persistence and printer-network reachability.
3. Add common pause/resume/cancel through typed capabilities and ADR 0004 command semantics.
4. Add realtime application events through WebSocket/SSE with reconnect/replay rules.
5. Connect queue lifecycle to automatic filament accounting and reconciliation.
6. Expose the existing guarded inventory mutation API through the web UI.
7. Build persistent farm scheduling with printer selection, priorities/deadlines and durable lease/CAS semantics.
8. Expand deep Bambu capabilities: AMS operations/drying, HMS, K profiles, dual-nozzle and validated X2D-specific behavior.

## Repository layout

```text
FoxForge/
├── backend/       Python 3.12+ domain, adapters, services, API and runtime
├── frontend/      TypeScript/React/Vite web application
├── deployment/    Docker and Umbrel deployment contracts/documentation
├── docs/          ADRs, design specifications and current project status
└── integrations/  isolated migration/provenance material
```

The layout is governed by [ADR 0002](docs/adr/0002-repository-layout.md).

## UmbrelOS

The published `v0.1.0-alpha.3` image is available through the companion Community App Store:

```text
https://github.com/MikeFox303/umbrel-3d-printing-store
```

Package ID: `my3d-foxforge`.

The package uses authenticated Umbrel App Proxy access, persistent `/data`, bridge networking and the immutable `alpha.3` multi-architecture GHCR digest. Future source changes are **not** delivered through a floating tag.

See [`deployment/umbrel/`](deployment/umbrel/README.md).

## Documentation

The Git repository is the canonical project record. Important documents:

- [Current project status](docs/project-status.md)
- [Documentation index](docs/README.md)
- [ADR 0001: PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md)
- [ADR 0002: Repository layout](docs/adr/0002-repository-layout.md)
- [ADR 0003: Upstream architecture synthesis](docs/adr/0003-upstream-architecture-synthesis.md)
- [ADR 0004: Command API security and idempotency](docs/adr/0004-command-api-security.md)
- [Printer contracts v1](docs/design/printer-contracts.md)
- [Bambu LAN transport](docs/design/bambu-lan-transport.md)
- [Bambu project storage](docs/design/bambu-project-storage.md)
- [Moonraker HTTP/WebSocket transport](docs/design/moonraker-http-transport.md)
- [Queue dispatch](docs/design/queue-dispatch.md)
- [Queue lifecycle](docs/design/queue-event-lifecycle.md)
- [Queue retry policy](docs/design/queue-retry-policy.md)
- [Queue command API and artifact staging](docs/design/queue-command-api.md)
- [Queue command UI](docs/design/queue-command-ui.md)
- [Inventory foundation](docs/design/inventory-foundation.md)
- [SQLite inventory persistence](docs/design/inventory-sqlite.md)
- [Web UI foundation](docs/design/web-ui-foundation.md)
- [Frontend parallel development policy](docs/design/frontend-parallel-development.md)

Repository guardrails also live in [`AGENTS.md`](AGENTS.md).

## Development

Backend:

```bash
git clone https://github.com/MikeFox303/FoxForge.git
cd FoxForge/backend
python -m venv .venv
# activate the environment
pip install -e ".[dev]"
pytest
ruff check src tests
ruff format --check src tests
```

Frontend:

```bash
cd ../frontend
npm install
npm run check
npm test
npm run build
```

Container/Compose documentation is under [`deployment/docker/`](deployment/docker/).

Implementation changes should define acceptance criteria and tests, preserve vendor boundaries and provenance, and document important architecture/runtime decisions in the repository.

## ❤️ Support FoxForge

FoxForge is free and open-source. If you find the project useful and would like to support continued development, test hardware and infrastructure, you can make a voluntary contribution on Ko-fi.

[☕ Support FoxForge on Ko-fi](https://ko-fi.com/mikefox303)

Support is completely optional and does not affect access to FoxForge or its source code.

## License

FoxForge is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.

See [`LICENSE`](LICENSE) for the full license text.
