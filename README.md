# FoxForge

[![Release](https://img.shields.io/badge/pre--release-v0.1.0--alpha.4.3-orange)](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)
[![Alpha 5](https://img.shields.io/badge/Alpha%205-Candidate%206%20published-yellow)](docs/project-status.md)
[![License](https://img.shields.io/badge/license-AGPL--3.0--only-blue)](LICENSE)
[![Platforms](https://img.shields.io/badge/Linux-amd64%20%7C%20arm64-lightgrey)](deployment/README.md)

**FoxForge is an open-source, self-hosted platform for managing mixed fleets of 3D printers through a vendor-independent core while preserving deep vendor-specific capabilities.**

Bambu Lab is the current primary integration target. Moonraker/Klipper is supported through the same common architecture, while material systems, queueing, filament accounting and future farm-management features remain capability-driven rather than tied to a single printer family.

> [!WARNING]
> FoxForge is early alpha software. Candidate 6 is published for controlled physical validation; it is **not production-ready** and publication/CI do not equal physical printer acceptance.

## Release and Candidate 6 status

The latest published semantic pre-release remains **[v0.1.0-alpha.4.3](https://github.com/MikeFox303/FoxForge/releases/tag/v0.1.0-alpha.4.3)**. Final **`v0.1.0-alpha.5` has not been published**.

Pre-Alpha 5 is tracked by [#115](https://github.com/MikeFox303/FoxForge/issues/115), with replacement Candidate 6 in [#154](https://github.com/MikeFox303/FoxForge/issues/154).

C6-10 and C6-11 are complete. The exact installable Candidate 6 identity is:

```text
FoxForge application source: 78ace6f7b7412aa0d3fc58bed095aecdf9920f94
C6-10 exact-main gate: run 34439269464 — PASS
image tag: ghcr.io/mikefox303/foxforge:sha-78ace6f
OCI digest: sha256:b01f1d44199a4413167ee2369c0dfbcafa602312442772d27de18e04c24ed0eb
exact image: ghcr.io/mikefox303/foxforge:sha-78ace6f@sha256:b01f1d44199a4413167ee2369c0dfbcafa602312442772d27de18e04c24ed0eb
publication verification: run 34440021792 — PASS
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.6
Umbrel Store PR: MikeFox303/umbrel-3d-printing-store#38
Umbrel Store commit: 018d29a8668e923c7f1a3447fc12273939aefbb8
Store post-merge package/runtime gate: run 34509996521 — PASS
Store post-merge release gate: run 34509996582 — PASS
target semantic release: v0.1.0-alpha.5 — not published
```

Candidate 5 is historical/failed for Alpha 5 acceptance. Candidate 1–5 evidence may not be relabeled as Candidate 6 evidence. Documentation-only commits after the frozen application source do not change Candidate 6 runtime identity.

**Candidate 6 physical validation is now authorized but has not yet been completed.** The next gate is the real Raspberry Pi 5 + Umbrel + X2D + AMS 2 Pro no-print procedure, followed by the first-print/accounting gate only after complete no-print PASS.

See the [current project status](docs/project-status.md), [Candidate 6 software gate](docs/testing/pre-alpha-5-candidate6-software-gate.md) and [physical-validation runbook](docs/testing/pre-alpha-5-bambu-physical-validation.md).

## What Candidate 6 provides

### Printer setup and fleet

- FoxForge-owned `PrinterAdapter` contracts with typed capability discovery;
- Bambu Lab LAN and Moonraker/Klipper adapters behind vendor-neutral application boundaries;
- application-managed Add / Update / Remove / Reconnect workflows;
- staged Add Printer **Provider → Connection → Identity → Verify** with exact-payload verification invalidation before Save;
- test-before-save for Add and Update, with rollback to the previous working adapter/configuration on failed replacement;
- bounded Bambu LAN discovery with manual fallback;
- restart-safe reconnect supervision with bounded backoff/jitter and secret-safe diagnostics.

### Deep Bambu Lab support

- MQTT/TLS live-state transport;
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
- P3 accounting reconstructed on the current architecture through R1–R5: durable reservations, no overcommit, idempotent settlement, fresh-routing pre-dispatch accounting guard, guarded reconciliation and operator accounting UI.

The generic runtime default remains `FOXFORGE_FILAMENT_ACCOUNTING_MODE=disabled`. The published Candidate 6 Umbrel package intentionally uses `bambu-validation`, which enforces accounting readiness only for Bambu adapters. Moonraker/Klipper automatic accounting remains disabled. FoxForge never infers consumed grams from progress and never auto-picks a spool or guesses a nozzle when routing is ambiguous.

Historical PR #58 is closed/unmerged and retained only as archive/reference.

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
| Bambu Lab adapter | Functional alpha; Candidate 6 physical validation next |
| Bambu LAN discovery | Implemented foundation; real deployment-network validation pending |
| Moonraker/Klipper adapter | Functional alpha; physical OpenKE validation pending |
| Common thermal telemetry | Bambu + Moonraker implementations integrated |
| Fleet/reconnect supervision | Implemented foundation |
| Durable print queue | Implemented foundation |
| Pause / Resume / Cancel | Implemented; physical validation pending |
| Artifact staging | Implemented |
| Filament/spool inventory | Operator workflow implemented |
| Automatic filament accounting | Bambu Candidate 6 validation mode published; physical acceptance pending |
| AMS/CFS observation | Bambu AMS + external source foundation implemented |
| Persistent farm scheduler | Not implemented |
| Docker `amd64` / `arm64` | Candidate 6 immutable image published and public runtime verified |
| Umbrel | Candidate 6 `0.1.0-alpha.4.3-umbrel.6` published/installable |

## Candidate 6 physical gate

Primary acceptance target:

```text
Raspberry Pi 5 + Umbrel
└─ FoxForge Candidate 6 (ordinary App Proxy / bridge networking)
   └─ Bambu Lab X2D + AMS 2 Pro
      ├─ A1 PETG
      ├─ A2 PETG
      ├─ A3 PETG
      ├─ A4 PETG
      ├─ External Left  -> left toolhead  -> empty
      └─ External Right -> right toolhead -> PLA
```

The no-print gate must prove install identity, GUI-only operator credential access, discovery/Add Printer, Verify→change→re-Verify, negative setup cases, rollback-safe Update, restart/reconnect recovery, redacted diagnostics, partial initial X2D status, thermal telemetry, AMS/external state and typed dual-external topology.

Only after every no-print section passes may the first-print path run:

```text
SHA256 → stage → inspect 3MF → select plate → explicit material bindings
→ routing compiler → accounting reservation → queue → explicit Start
→ FTPS → project_file → exactly one observed physical job
```

Physical accounting evidence must include the exact FoxForge spool assignment/reservation and reproducible pre/post measured spool mass. Do not derive actual grams from progress.

Any application-code, image or package-definition change after physical evidence begins requires a new candidate. Documentation/evidence commits do not change the frozen Candidate 6 application identity.

## Installation

### Umbrel

FoxForge Candidate 6 is available from the [MikeFox303 3D Printing Community App Store](https://github.com/MikeFox303/umbrel-3d-printing-store) as `my3d-foxforge` version `0.1.0-alpha.4.3-umbrel.6`.

Add/refresh that Community Store in Umbrel, select FoxForge, and install/update normally. The package uses ordinary bridge/App Proxy networking, no host networking, and maps Umbrel `${APP_PASSWORD}` to `FOXFORGE_COMMAND_TOKEN`. Enter the app password shown by Umbrel in **Operator Access / Unlock writes**; the browser retains it only in memory for the current tab.

See [Umbrel deployment](deployment/umbrel/README.md).

### Docker

Candidate 6 can also be pulled by exact immutable identity:

```bash
docker pull ghcr.io/mikefox303/foxforge:sha-78ace6f@sha256:b01f1d44199a4413167ee2369c0dfbcafa602312442772d27de18e04c24ed0eb
```

The latest semantic release image remains:

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
- [Candidate 6 software gate](docs/testing/pre-alpha-5-candidate6-software-gate.md)
- [Pre-Alpha 5 physical-validation runbook](docs/testing/pre-alpha-5-bambu-physical-validation.md)
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
