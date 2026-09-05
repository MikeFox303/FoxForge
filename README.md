# FoxForge

**FoxForge is an open-source, self-hosted platform for managing mixed fleets of 3D printers without sacrificing deep vendor-specific functionality.**

FoxForge combines a vendor-independent printer/application core with deep Bambu Lab support, Moonraker/Klipper support, durable print queues, filament/spool inventory, material-system integration, farm workflows and Docker/Umbrel deployment.

> **Published pre-release:** `v0.1.0-alpha.4`  
> **Published release commit:** `457f8f3f044147772b1ecf13df90b38a35268cda`  
> **Published image:** `ghcr.io/mikefox303/foxforge:0.1.0-alpha.4`  
> **Multi-arch digest:** `sha256:0b0d96e5243db82ad3349bbc1c96243cbc6288c27eb716ff80512eb925b9fef4`  
> **Umbrel package:** `my3d-foxforge` `0.1.0-alpha.4`, merged to Store `main` via PR #26 (`de430fe63d79843b0a646851e8f03b05e37f624d`)  
> **Maturity:** runnable/installable alpha, **not production-ready**. Representative physical Bambu X2D, Moonraker/OpenKE and Raspberry Pi/Umbrel validation is still required.

## What FoxForge currently implements

`v0.1.0-alpha.4` and its frozen release source include:

- FoxForge-owned `PrinterAdapter` contracts with typed capability discovery;
- Bambu Lab and Moonraker/Klipper adapters behind a vendor-neutral application boundary;
- `FleetService`, durable SQLite queueing and restart-safe per-printer reconnect supervision;
- typed common `foxforge.job_control` v1 with exact vendor-job identity guards for Pause/Resume/Cancel;
- Bambu MQTT/TLS and project-storage foundations with optional independent MQTT/FTPS SHA-256 certificate pins;
- Moonraker HTTP/WebSocket transport with explicit endpoint/address/redirect security policy;
- authenticated/idempotent printer, queue, inventory and job-control command APIs with append-only audit;
- a `SecretStore` boundary separating printer credentials from ordinary runtime configuration;
- versioned config/SQLite persistence migrations with backups and validation;
- content-addressed `.gcode`/`.3mf` artifact staging with quota, free-space reserve and safe garbage collection;
- durable filament/spool inventory with exact `Decimal` accounting and opaque physical slot assignments;
- complete normal inventory operator workflow: create, correct mass, edit empty-spool mass, assign/move/unassign, archive and inspect history;
- FoxForge-owned SSE application events with replay/resync semantics and TanStack Query invalidation;
- React + TypeScript + Vite UI with EN/RU/UK localization;
- production-container browser acceptance on desktop, tablet and phone layouts;
- Docker and Linux `amd64`/`arm64` guarded release publication with SBOM/provenance;
- frozen frontend/backend dependency graphs, dependency audits, final-image vulnerability scanning and measured backend branch-coverage governance.

Automatic filament accounting is **not** part of `alpha.4`. The partial P3 work remains frozen in draft PR #58 behind the physical/deployment validation gate.

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

Common application/domain code must not import Bambu or Moonraker transport types. Deep Bambu features remain first-class typed capabilities instead of being flattened into a lowest-common-denominator interface.

FoxForge uses upstream projects as specialized references:

- **Bambuddy** — Bambu protocol/product-behavior reference;
- **PrintBuddy** — multi-vendor/provider-isolation reference;
- **PrintOps** — farm/operations/scheduling reference;
- **FoxForge** — owner of the common contracts, API/frontend boundaries, queue, inventory and deployment behavior.

See [ADR 0001](docs/adr/0001-printer-adapter-architecture.md), [ADR 0003](docs/adr/0003-upstream-architecture-synthesis.md) and the [Upstream adoption map](docs/design/upstream-adoption-map.md).

## Safety model

FoxForge treats uncertain printer side effects conservatively:

- remote writes use authentication, authorization, validation, durable idempotency, normalized errors and audit;
- queue `dispatch_id`, job-control `controlId` and HTTP `Idempotency-Key` remain distinct identities;
- an `INDETERMINATE` print-start/control outcome is never blindly retried;
- receipt-bearing jobs are never redispatched;
- browser code cannot weaken backend retry/reconciliation semantics;
- realtime events are invalidations only; HTTP snapshots remain canonical;
- durable queue/inventory events publish only after successful persistence;
- printer credentials are hydrated only at runtime boundaries through `SecretStore`;
- Moonraker destinations fail closed outside the configured LAN/override policy;
- optional Bambu certificate pins fail closed on mismatch without exposing fingerprints.

See [ADR 0004](docs/adr/0004-command-api-security.md), [ADR 0005](docs/adr/0005-browser-command-authentication.md), [Queue dispatch](docs/design/queue-dispatch.md), [Realtime events](docs/design/realtime-events.md), [Moonraker transport](docs/design/moonraker-http-transport.md) and [Bambu certificate trust](docs/design/bambu-certificate-trust.md).

## Web interface

The `alpha.4` UI supports live fleet/queue/inventory reads, printer setup, browser artifact hashing/staging, durable enqueue/dispatch/reconciliation, capability-gated Pause/Resume/Cancel and the complete normal inventory operator workflow.

Production-container Playwright acceptance covers desktop, tablet and phone layouts, routing, Add Printer keyboard behavior, memory-only operator write bootstrap, browser file staging/enqueue, realtime `resync_required` refetch and representative inventory create/correct/assignment/history/archive behavior. Periodic polling remains an alpha fallback.

## Runtime and persistence

The unified `aiohttp` runtime serves the API and compiled SPA. Persistent `/data` contains app-owned configuration, `foxforge.sqlite3`, printer secrets and staged artifacts.

Current persistence ownership is explicit:

- `config.json` schema version: **2**;
- SQLite `PRAGMA user_version`: **1**;
- `secrets.json` SecretStore format version: **1**.

Configuration and SQLite migrations are versioned and backed up before migration. `/data` must be treated as sensitive deployment data.

## Current status

| Area | `v0.1.0-alpha.4` / current release source |
| --- | --- |
| Common printer domain | Implemented |
| Bambu adapter | LAN/control foundation implemented; optional cert pinning implemented; physical X2D validation pending |
| Moonraker adapter | HTTP/WebSocket/control foundation implemented; endpoint policy implemented; physical OpenKE validation pending |
| Fleet management | Implemented |
| Durable queue | Implemented foundation with lifecycle/retry/reconciliation |
| Artifact staging | Implemented with capacity/GC controls |
| Filament inventory | Durable SQLite foundation + full normal operator workflow implemented |
| Command auth/idempotency/audit | Implemented foundation |
| Secret storage boundary | Implemented |
| Pause/Resume/Cancel | Implemented and released; physical printer validation pending |
| Realtime application events | Implemented and released through SSE replay/resync + query invalidation |
| Browser acceptance | Production-container desktop/tablet/phone matrix implemented |
| Backend coverage governance | ~76% measured baseline; 75% branch-aware CI floor |
| Automatic filament accounting | **Frozen draft in PR #58; not merged** |
| Farm scheduler | Not implemented |
| Docker/ARM64 | `alpha.4` published for `amd64` + `arm64`; representative hardware validation pending |
| Umbrel | `my3d-foxforge` `0.1.0-alpha.4` is merged in Store `main`, pinned to the immutable release digest and configured with `APP_PASSWORD` → `FOXFORGE_COMMAND_TOKEN`; physical Raspberry Pi/Umbrel evidence remains pending |

## Independent audit and development order

The independent audit snapshot is [`docs/audits/2026-09-04-independent-project-audit.md`](docs/audits/2026-09-04-independent-project-audit.md). Active remediation status is tracked separately in [`docs/audits/2026-09-04-remediation-tracker.md`](docs/audits/2026-09-04-remediation-tracker.md).

All software-only findings have repository remediation evidence. The remaining unresolved audit findings are validation-bound:

- **AUD-003** — representative Raspberry Pi/Umbrel package/deployment evidence;
- **AUD-013** — real Bambu X2D MQTT/FTPS certificate observations.

P3 automatic filament accounting is preserved in draft PR #58 and remains frozen. The detailed resume contract is [`docs/status/p3-frozen-state-2026-09-04.md`](docs/status/p3-frozen-state-2026-09-04.md).

### Current development priorities

1. Record representative **Bambu X2D**, **Moonraker/OpenKE** and **Raspberry Pi 5/Umbrel** evidence required by AUD-003/AUD-013 and the P3 resume gate.
2. Keep deployment/package documentation aligned with what was actually validated; do not convert CI/QEMU evidence into physical support claims.
3. Resume **P3 automatic filament accounting** only after the physical/deployment gate passes, synchronize draft PR #58 with then-current `main`, preserve all stabilization changes and rerun exact-head backend/frontend/container/security/browser gates.
4. After P3 is safely integrated, continue persistent farm scheduling and deeper Bambu capabilities behind typed vendor interfaces.

The inventory operator workflow is complete and is no longer an outstanding prerequisite.

## Hardware validation still required

FoxForge must not yet claim production-ready printer support. Required real-device/deployment evidence includes:

1. **Bambu X2D / Bambu LAN** — connection/reconnect, state synchronization, certificate observations, project delivery, print-start acknowledgement, pause/resume/cancel, lifecycle and ambiguous-outcome reconciliation.
2. **Moonraker/OpenKE** — HTTP/WebSocket connectivity, endpoint policy against the real printer address, upload/start, pause/resume/cancel and lifecycle completion/failure behavior.
3. **Raspberry Pi 5 / UmbrelOS** — install/restart/persistence, printer reachability from the actual Umbrel network, authenticated proxy/write behavior, upgrade behavior and representative SSE reconnect/resync behavior.

Automated CI, QEMU and browser tests are required but do not replace these physical matrices.

## Repository layout

```text
FoxForge/
├── backend/       Python 3.12+ domain, adapters, services, API and runtime
├── frontend/      TypeScript/React/Vite web application
├── deployment/    Docker and Umbrel deployment contracts/documentation
├── docs/          ADRs, design specifications, audit and project status
└── integrations/  isolated migration/provenance material
```

Repository guardrails live in [`AGENTS.md`](AGENTS.md).

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

Coverage policy is documented in [`docs/testing/coverage-policy.md`](docs/testing/coverage-policy.md). Container/Compose documentation is under [`deployment/docker/`](deployment/docker/).

## Documentation

Important current documents:

- [Project status](docs/project-status.md)
- [Documentation index](docs/README.md)
- [Independent audit](docs/audits/2026-09-04-independent-project-audit.md)
- [Audit remediation tracker](docs/audits/2026-09-04-remediation-tracker.md)
- [P3 frozen state and resume gate](docs/status/p3-frozen-state-2026-09-04.md)
- [PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md)
- [Browser command authentication/deployment trust](docs/adr/0005-browser-command-authentication.md)
- [Bambu LAN transport](docs/design/bambu-lan-transport.md)
- [Moonraker transport](docs/design/moonraker-http-transport.md)
- [Secret storage](docs/design/secret-storage.md)
- [Persistent migrations](docs/design/persistence-migrations.md)
- [Release notes: v0.1.0-alpha.4](release/v0.1.0-alpha.4.md)

## ❤️ Support FoxForge

FoxForge is free and open-source. If you find the project useful and would like to support continued development, test hardware and infrastructure, you can make a voluntary contribution on Ko-fi.

[☕ Support FoxForge on Ko-fi](https://ko-fi.com/mikefox303)

Support is completely optional and does not affect access to FoxForge or its source code.

## License

FoxForge is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.

See [`LICENSE`](LICENSE) for the full license text.
