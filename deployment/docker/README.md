# Docker deployment

FoxForge has a runnable alpha Docker implementation in this directory. The current published deployment line is `v0.1.0-alpha.4.2`.

## Implemented

- multi-stage production image;
- compiled React/Vite frontend included in the final runtime image;
- Python `foxforge` server serving both the SPA and `/api/v1`;
- standalone `docker-compose.yml`;
- persistent application data mounted at `/data`;
- safe first-start creation of `config.json` schema 2 and `foxforge.sqlite3`;
- versioned persistence migrations and backups;
- `SecretStore` boundary for printer credentials;
- staged print artifacts under `/data/artifacts` with quota/free-space/orphan controls;
- mounted-data permission preparation followed by non-root steady-state execution;
- container health/startup smoke tests in CI;
- immutable versioned release publication for Linux `amd64` and `arm64`;
- SBOM/provenance metadata on the published multi-architecture release image;
- anonymous pull/start/runtime smoke validation for both published architectures;
- no development-time Node.js server in the production image;
- no Docker socket requirement;
- no `network_mode: host` requirement for the current explicit-IP Bambu/Moonraker model;
- application-level authenticated/idempotent command APIs;
- common Pause/Resume/Cancel and SSE application events included in the current release line;
- complete normal inventory operator workflow included in the current release line;
- production-container Browser Acceptance covering phone, tablet, 16:9 desktop and 32:9 ultra-wide layouts, including Add Printer and Operator Access regressions;
- the same application image is reused by the Umbrel Community App package.

The current image is suitable for development and controlled alpha testing. It is not yet production-ready because representative hardware and printer-network validation remain incomplete.

## Published image

```text
ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6
```

The digest identifies the guarded Linux `amd64` + `arm64` OCI index published from release commit `fe5b3437f1e342548df74ded78557c771ef40710`.

## Runtime expectations

The container owns one FoxForge application runtime:

```text
browser
  |
FoxForge container
  ├── React SPA
  ├── /api/v1 reads + guarded commands
  ├── /api/v1/events SSE invalidations
  ├── FleetService / QueueService / InventoryService
  ├── SQLite + SecretStore state
  ├── /data/artifacts
  └── outbound connections to configured printers
```

Persistent state and printer credentials remain outside the immutable image under `/data`.

Printer configuration is normally performed through the FoxForge UI/API. Direct configuration-file editing is an administrative fallback, not the primary setup path.

## Write authentication

Standalone Docker can run in two deliberate modes:

- **write-enabled:** set `FOXFORGE_COMMAND_TOKEN` to a high-entropy token and enter the same token in **Unlock writes** in the browser;
- **read-only:** omit the token; reads remain available while protected commands fail closed.

Use `deployment/docker/.env.example` as the configuration template. The browser keeps the operator token only in memory for the current tab.

`FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is not a supported shortcut and is rejected by the production runtime.

## Release and upgrade model

`v0.1.0-alpha.4.2` is published as an immutable multi-architecture release image. Source changes merged after release are not delivered to existing deployments through a floating semantic release tag; they require another guarded release.

Persistence compatibility is still pre-stable even though migration ownership exists. Back up the complete `/data` directory before upgrading between early alpha releases and treat backups as sensitive because credentials/recovery material may be included.

The matching Umbrel package is pinned to the same semantic version plus immutable OCI digest in Store commit `e842c411e26689609e9bbba4681df903f3624bbd`.

## Remaining production-readiness work

- representative Raspberry Pi 5 / physical ARM64 runtime validation;
- physical Bambu LAN/X2D and Moonraker/OpenKE connectivity, upload/start/control/lifecycle/reconciliation validation;
- real deployment-network compatibility for printer access;
- representative upgrade testing across published tagged releases;
- representative reverse-proxy/SSE reconnect-resync behavior;
- network/design validation before discovery, Virtual Printer or other features requiring broader LAN behavior are enabled;
- P3 automatic filament accounting remains frozen until the physical/deployment gate passes.

Use `docs/testing/physical-validation-runbook.md` for the exact Alpha 4.2 physical-test identity and evidence procedure.
