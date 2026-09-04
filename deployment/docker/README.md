# Docker deployment

FoxForge now has a runnable alpha Docker implementation in this directory.

## Implemented

- multi-stage production image;
- compiled React/Vite frontend included in the final runtime image;
- Python `foxforge` server serving both the SPA and `/api/v1`;
- standalone `docker-compose.yml`;
- persistent application data mounted at `/data`;
- safe first-start creation of `config.json` and `foxforge.sqlite3`;
- mounted-data permission preparation followed by non-root steady-state execution;
- container health/startup smoke test in CI;
- no development-time Node.js server in the production image;
- no Docker socket requirement;
- no `network_mode: host` requirement for the current explicit-IP Bambu/Moonraker alpha model.

The current image is suitable for development and controlled alpha testing. It is not yet a production release.

## Runtime expectations

The container owns one FoxForge application runtime:

```text
browser
  |
FoxForge container
  ├── React SPA
  ├── /api/v1
  ├── FleetService / QueueService / InventoryService
  ├── SQLite state
  └── outbound connections to configured printers
```

Persistent state and printer credentials remain outside the immutable image under `/data`.

## Release gates still pending

- immutable tagged/digest image publication policy;
- representative Linux ARM64 runtime validation in addition to build preparation;
- upgrade/migration rules for persisted configuration/database state;
- physical Bambu LAN/X2D and Moonraker/OpenKE validation;
- hardened command/authentication API before remote writes are exposed;
- Umbrel end-to-end packaging built from the same application image.
