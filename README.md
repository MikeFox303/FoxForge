# FoxForge

**FoxForge is an open-source, self-hosted platform for managing mixed fleets of 3D printers without sacrificing deep vendor-specific functionality.**

FoxForge combines a vendor-independent printer/application core with deep Bambu Lab support, Moonraker/Klipper support, durable print queues, filament/spool inventory, material-system integration, farm workflows and Docker/Umbrel deployment.

> **Published release:** `v0.1.0-alpha.3`  
> **Current source state:** development has moved beyond the immutable `alpha.3` image. Current `main` contains P1 common Pause/Resume/Cancel, P2 realtime application events and the independent-audit stabilization work merged after those milestones.  
> **Maturity:** runnable/installable alpha, **not production-ready**. Representative physical Bambu X2D, Moonraker/OpenKE and Raspberry Pi/Umbrel validation is still required.

## What FoxForge currently implements

Current `main` includes:

- FoxForge-owned `PrinterAdapter` contracts with typed capability discovery;
- Bambu Lab and Moonraker/Klipper adapters behind a vendor-neutral application boundary;
- `FleetService`, durable SQLite queueing and restart-safe reconnect supervision;
- typed common `foxforge.job_control` v1 with exact vendor-job identity guards;
- Bambu MQTT/TLS and project-storage foundations with optional independent MQTT/FTPS SHA-256 certificate pins;
- Moonraker HTTP/WebSocket transport with explicit RFC1918/ULA endpoint policy, redirect rejection and advanced endpoint overrides;
- authenticated/idempotent printer, queue, inventory and job-control command APIs with append-only audit;
- a `SecretStore` boundary separating printer credentials from ordinary runtime configuration;
- content-addressed `.gcode`/`.3mf` artifact staging with quota, free-space reserve and safe garbage collection;
- durable filament/spool inventory with exact `Decimal` accounting and opaque physical slot assignments;
- FoxForge-owned SSE application events with replay/resync semantics and TanStack Query invalidation;
- React + TypeScript + Vite UI with EN/RU/UK localization;
- production-container browser acceptance on desktop, tablet and phone layouts;
- Docker, Linux `amd64`/`arm64`, Compose and Umbrel packaging foundations;
- frozen frontend/backend dependency graphs, dependency audits, final-image vulnerability scanning and measured backend branch-coverage governance.

The shipped `v0.1.0-alpha.3` image is immutable and predates P1, P2 and the later audit-remediation work. A later guarded release is required before versioned Docker/Umbrel users receive the current source state.

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

See [ADR 0004](docs/adr/0004-command-api-security.md), [ADR 0005](docs/adr/0005-browser-deployment-trust.md), [Queue dispatch](docs/design/queue-dispatch.md), [Realtime events](docs/design/realtime-events.md), [Moonraker transport](docs/design/moonraker-http-transport.md) and [Bambu certificate trust](docs/design/bambu-certificate-trust.md).

## Web interface

The UI currently supports live fleet/queue/inventory reads, printer setup, browser artifact hashing/staging, durable enqueue/dispatch/reconciliation and capability-gated Pause/Resume/Cancel.

Production-container Playwright acceptance covers desktop, tablet and phone projects, routing, the single Add Printer launcher, Escape-close keyboard behavior, memory-only operator write bootstrap, truthful unavailable states, browser file staging/enqueue and deterministic SSE `resync_required` HTTP refetch. Periodic polling remains an alpha fallback.

The normal inventory operator workflow is not complete yet. Before automatic accounting resumes, the UI must provide a coherent create/correct/move/assign/unassign/archive/history workflow for reconciliation and day-to-day spool management.

## Runtime and persistence

The unified `aiohttp` runtime serves the API and compiled SPA. Persistent `/data` contains app-owned configuration, `foxforge.sqlite3`, printer secrets and staged artifacts.

Configuration and SQLite migrations are versioned and backed up before migration. Printer credentials are stored behind a replaceable `SecretStore` infrastructure port; the current file backend remains sensitive deployment data and does not make `/data` safe to expose or publish.

## Current status

| Area | Current source state |
| --- | --- |
| Common printer domain | Implemented |
| Bambu adapter | LAN/control foundation implemented; optional cert pinning implemented; physical X2D validation pending |
| Moonraker adapter | HTTP/WebSocket/control foundation implemented; endpoint policy implemented; physical OpenKE validation pending |
| Fleet management | Implemented |
| Durable queue | Implemented foundation with lifecycle/retry/reconciliation |
| Artifact staging | Implemented with capacity/GC controls |
| Filament inventory | Durable SQLite foundation implemented |
| Command auth/idempotency/audit | Implemented foundation |
| Secret storage boundary | Implemented |
| Realtime application events | Implemented through SSE replay/resync + query invalidation |
| Browser acceptance | Production-container desktop/tablet/phone matrix implemented |
| Backend coverage governance | 76% measured baseline; 75% branch-aware CI floor |
| Automatic filament accounting | **Frozen draft in PR #58; not merged into `main`** |
| Inventory operator workflow | Incomplete |
| Farm scheduler | Not implemented |
| Docker/ARM64 | Implemented foundation; representative hardware validation pending |
| Umbrel | Released package remains on immutable `alpha.3`; current source not yet released |

## Independent audit and development order

The independent audit snapshot is [`docs/audits/2026-09-04-independent-project-audit.md`](docs/audits/2026-09-04-independent-project-audit.md). Active remediation status is tracked separately in [`docs/audits/2026-09-04-remediation-tracker.md`](docs/audits/2026-09-04-remediation-tracker.md).

P3 automatic filament accounting is preserved in draft PR #58, but it is intentionally frozen. The detailed resume contract is [`docs/status/p3-frozen-state-2026-09-04.md`](docs/status/p3-frozen-state-2026-09-04.md).

### Current development priorities

1. Complete representative **Bambu X2D**, **Moonraker/OpenKE** and **Raspberry Pi 5/Umbrel** validation required by the remaining audit findings.
2. Complete the normal inventory operator workflow: create, correct, move, assign, unassign, archive and inspect history/reconciliation state.
3. Record the physical/deployment evidence and close the remaining validation-only audit items where the evidence supports it.
4. Only then resume **P3 automatic filament accounting** by synchronizing draft PR #58 with current `main`, preserving all stabilization changes and rerunning exact-head backend/frontend/container/security/browser gates.
5. After P3 is safely integrated, continue persistent farm scheduling and deeper Bambu capabilities behind typed vendor interfaces.

This ordering supersedes older current-status wording that described P3 as the immediate next implementation priority. Historical release notes remain historical and are not rewritten.

## Hardware validation still required

FoxForge must not yet claim production-ready printer support. Required real-device/deployment evidence includes:

1. **Bambu X2D / Bambu LAN** — connection/reconnect, state synchronization, certificate observations, project delivery, print-start acknowledgement, pause/resume/cancel, lifecycle and ambiguous-outcome reconciliation.
2. **Moonraker/OpenKE** — HTTP/WebSocket connectivity, endpoint policy against the real printer address, upload/start, pause/resume/cancel and lifecycle completion/failure behavior.
3. **Raspberry Pi 5 / UmbrelOS** — install/restart/persistence, printer reachability from the actual Umbrel network, authenticated proxy/write behavior and representative SSE behavior through the deployed proxy path.

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
- [Browser/deployment trust](docs/adr/0005-browser-deployment-trust.md)
- [Bambu LAN transport](docs/design/bambu-lan-transport.md)
- [Moonraker transport](docs/design/moonraker-http-transport.md)
- [Secret storage](docs/design/secret-storage.md)
- [Persistent migrations](docs/design/persistence-migrations.md)

## ❤️ Support FoxForge

FoxForge is free and open-source. If you find the project useful and would like to support continued development, test hardware and infrastructure, you can make a voluntary contribution on Ko-fi.

[☕ Support FoxForge on Ko-fi](https://ko-fi.com/mikefox303)

Support is completely optional and does not affect access to FoxForge or its source code.

## License

FoxForge is licensed under the **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**.

See [`LICENSE`](LICENSE) for the full license text.
