# FoxForge backend

The backend is the Python 3.12+ application/core runtime for FoxForge.

## Responsibilities

It owns:

- FoxForge printer, queue and inventory domain contracts;
- `PrinterAdapter` and typed capability boundaries;
- Bambu Lab and Moonraker/Klipper adapters and transports;
- `FleetService`, durable queue and inventory application services;
- application-managed printer configuration, test-before-save and rollback-safe updates;
- Bambu LAN discovery and secret-safe reconnect diagnostics;
- authenticated/idempotent command APIs and append-only command audit;
- `/api/v1` HTTP read/command models and `/api/v1/events` SSE invalidations;
- SQLite persistence, migrations, artifact staging and `SecretStore` credential handling;
- the unified `aiohttp` runtime that serves both API and compiled frontend assets.

The backend must remain independent from frontend implementation details. HTTP/SSE handlers call application services and typed capabilities; they do not bypass those boundaries to raw Bambu/Moonraker transports.

## Architecture rule

```text
HTTP / runtime
      |
application services
      |
PrinterAdapter + typed capabilities
      |
Bambu / Moonraker adapters
      |
vendor transports
```

Common domain/application packages must not import vendor protocol DTOs or transport implementations.

## Development

```bash
python -m venv .venv
# activate the environment
pip install -c constraints.txt -e ".[dev]"
pytest
ruff check src tests
ruff format --check src tests
```

See [`../docs/README.md`](../docs/README.md) for the current architecture and validation documentation.
