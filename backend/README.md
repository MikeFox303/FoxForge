# FoxForge backend

The FoxForge backend is the Python 3.12+ application/core runtime.

It owns:

- the normalized printer domain;
- `PrinterAdapter` contracts and typed capabilities;
- Bambu Lab and Moonraker/Klipper adapters;
- fleet and durable print-queue application services;
- persistence/database infrastructure;
- future inventory and AMS/CFS application workflows;
- the future public REST/WebSocket API used by the web frontend and automation clients.

The backend must remain independent from frontend implementation details. HTTP/WebSocket handlers should call application services and typed capabilities rather than importing vendor protocol transports directly.

## Development

From this directory:

```bash
python -m venv .venv
# Activate the virtual environment, then:
pip install -e ".[dev]"
pytest
ruff check src tests
ruff format --check src tests
```

See the repository-level `docs/` directory for architecture decisions and design specifications.
