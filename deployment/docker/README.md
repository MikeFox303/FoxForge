# Docker deployment

FoxForge provides a unified production-style container for controlled alpha testing and self-hosted development.

## Published semantic release

The latest semantic release image is:

```text
ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.3
```

Release tags are immutable publication identities. Changes merged after a semantic release require another guarded release.

## Pre-Alpha 5 validation image

The current Umbrel physical-validation candidate is built from a development SHA and is documented here only so tests can reproduce the exact application image:

```text
ghcr.io/mikefox303/foxforge:sha-37d1cbe@sha256:4e652006212db2527804abbd478b7b64fde127414b1dbe22703854280ccfce82
```

Source commit: `37d1cbed8f73d62acdc1994545bc2f5ee57e816a`. This is Candidate 3 and replaces Candidate 2 for current physical evidence because print material routing and Bambu native nozzle mapping changed after the earlier image.

Do not present this SHA image as `v0.1.0-alpha.5`.

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

Standalone Docker supports two intentional modes:

- **write-enabled:** set a strong `FOXFORGE_COMMAND_TOKEN` and enter it in **Operator Access / Unlock writes**;
- **read-only commands:** omit the token; read endpoints remain available while protected mutations fail closed.

Use `.env.example` as the configuration template. The browser keeps the token only in memory for the current tab.

`FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is unsupported and rejected by production startup.

## Start with Compose

```bash
cd deployment/docker
cp .env.example .env
# set FOXFORGE_COMMAND_TOKEN in .env when write access is required
docker compose up -d
```

Printer setup is normally performed in the FoxForge UI. Direct editing of `/data/config.json` is an administrative fallback, not the primary setup path.

## Upgrade safety

Back up the complete `/data` directory before early-alpha upgrades. It can contain printer credentials and recovery material.

For current physical-validation instructions see [`../../docs/testing/pre-alpha-5-bambu-physical-validation.md`](../../docs/testing/pre-alpha-5-bambu-physical-validation.md).
