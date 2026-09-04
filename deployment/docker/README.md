# Docker deployment

FoxForge has a runnable alpha Docker implementation in this directory. The current published deployment line is `v0.1.0-alpha.3`.

## Implemented

- multi-stage production image;
- compiled React/Vite frontend included in the final runtime image;
- Python `foxforge` server serving both the SPA and `/api/v1`;
- standalone `docker-compose.yml`;
- persistent application data mounted at `/data`;
- safe first-start creation of `config.json` and `foxforge.sqlite3`;
- staged print artifacts persisted under `/data/artifacts`;
- mounted-data permission preparation followed by non-root steady-state execution;
- container health/startup smoke test in CI;
- immutable versioned release publication for Linux `amd64` and `arm64`;
- SBOM/provenance metadata on the published multi-architecture release image;
- anonymous pull/start/runtime smoke validation for both published architectures;
- no development-time Node.js server in the production image;
- no Docker socket requirement;
- no `network_mode: host` requirement for the current explicit-IP Bambu/Moonraker model;
- application-level authenticated/idempotent command APIs for released remote writes;
- the same application image is reused by the Umbrel Community App package.

The current image is suitable for development and controlled alpha testing. It is not yet production-ready because representative hardware and printer-network validation remain incomplete.

## Runtime expectations

The container owns one FoxForge application runtime:

```text
browser
  |
FoxForge container
  ├── React SPA
  ├── /api/v1 reads + guarded commands
  ├── FleetService / QueueService / InventoryService
  ├── SQLite state
  ├── /data/artifacts
  └── outbound connections to configured printers
```

Persistent state and printer credentials remain outside the immutable image under `/data`.

Printer configuration is normally performed through the released FoxForge UI/API. Direct configuration-file editing is not the primary alpha.3 setup path.

## Release and upgrade model

`v0.1.0-alpha.3` is published as an immutable multi-architecture release image. Future source changes are not delivered to existing deployments through a floating tag; they require another guarded release.

Persistence compatibility is still pre-stable. Back up `/data` before upgrading between early alpha releases.

## Remaining production-readiness work

- representative Raspberry Pi 5 / physical ARM64 runtime validation;
- physical Bambu LAN/X2D and Moonraker/OpenKE connectivity, upload/start/lifecycle/reconciliation validation;
- persisted-state upgrade/migration compatibility policy;
- upgrade testing across later tagged releases;
- network/design validation before discovery, Virtual Printer or other features requiring broader LAN behavior are enabled.
