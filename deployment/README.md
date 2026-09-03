# FoxForge deployment

Deployment assets live separately from backend and frontend source code.

Current target families:

- `docker/` — container image and compose/runtime packaging;
- `umbrel/` — Umbrel application packaging built on the same container/runtime contract.

Deployment code must not become a second application implementation. Docker and Umbrel should package the same FoxForge backend plus compiled frontend assets, with configuration supplied through documented environment/runtime settings.
