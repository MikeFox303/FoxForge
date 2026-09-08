# Docker deployment

FoxForge provides a unified production-style container for controlled alpha testing and self-hosted development.

## Published semantic release

The latest semantic release image is:

```text
ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.3
```

Release tags are immutable publication identities. Changes merged after a semantic release require another guarded release.

## Pre-Alpha 5 validation image

The currently published physical-validation package remains Candidate 5 until Candidate 6 is frozen and published. Candidate 6 development must not be represented as physically validated before its exact source/image/Umbrel identity exists.

## Implemented runtime

- multi-stage frontend/backend build;
- compiled React/Vite assets served by the Python runtime;
- `/api/v1` reads and guarded commands;
- `/api/v1/events` SSE invalidations;
- persistent `/data` for config, SQLite, SecretStore and staged artifacts;
- versioned migrations/backups;
- non-root steady-state execution;
- health/startup and browser acceptance in CI;
- Linux `amd64` and `arm64` release publication;
- no Docker socket or privileged-mode requirement;
- no host-network requirement for current explicit-address transports;
- Bambu discovery available when the selected private subnet is reachable from the container network namespace.

## Write authentication

Standalone Docker supports two intentional command-auth modes:

- **write-enabled:** set a strong `FOXFORGE_COMMAND_TOKEN` and enter it in **Operator Access / Unlock writes**;
- **read-only commands:** omit the token; read endpoints remain available while protected mutations fail closed.

Use `.env.example` as the configuration template. The browser keeps the token only in memory for the current tab.

`FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is unsupported and rejected by production startup.

## Filament-accounting enforcement mode

Candidate 6 introduces an explicit runtime mode for the P3 pre-dispatch accounting gate:

```text
FOXFORGE_FILAMENT_ACCOUNTING_MODE=disabled
```

Supported values are deliberately closed:

- `disabled` — default for ordinary Docker/self-hosted deployments; accounting read/write/reconciliation remains available, but no provider is forced through the pre-dispatch reservation gate;
- `bambu-validation` — controlled Candidate 6 validation mode; only printers whose configured `adapter_kind` is `bambu` are required to pass the existing vendor-independent filament-accounting policy before the queue can cross `DISPATCHING`.

`bambu-validation` does **not** infer consumed grams from print progress, does not change Bambu transport commands, and does not enable Moonraker/Klipper accounting. It only activates the already-tested common reservation/assignment/capacity gate for Bambu queue entries. Missing reservations, changed physical-slot assignments or insufficient held capacity remain fail-closed before printer side effects.

The mode is reported in `/api/v1/diagnostics/persistence` so validation evidence can prove which enforcement boundary was active.

## Start with Compose

```bash
cd deployment/docker
cp .env.example .env
# set FOXFORGE_COMMAND_TOKEN in .env when write access is required
docker compose up -d
```

For normal use, leave `FOXFORGE_FILAMENT_ACCOUNTING_MODE=disabled`. Only the Candidate 6 physical-validation procedure may set `bambu-validation` before provider evidence is accepted.

Printer setup is normally performed in the FoxForge UI. Direct editing of `/data/config.json` is an administrative fallback, not the primary setup path.

## Upgrade safety

Back up the complete `/data` directory before early-alpha upgrades. It can contain printer credentials and recovery material.

For current physical-validation instructions see [`../../docs/testing/pre-alpha-5-bambu-physical-validation.md`](../../docs/testing/pre-alpha-5-bambu-physical-validation.md).
