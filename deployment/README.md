# FoxForge deployment

Deployment assets live separately from backend and frontend source code, but package the same FoxForge application.

## Current status

The Docker deployment is now a runnable alpha implementation rather than a placeholder:

- one multi-stage image builds the React frontend and Python backend;
- one `aiohttp` runtime serves the compiled SPA and `/api/v1`;
- standalone Compose configuration is available under `docker/`;
- application state is persisted outside the image under `/data`;
- first start creates safe local configuration/database state;
- the container prepares mounted data permissions before dropping to a non-root steady-state user;
- CI builds and starts the container, checks `/healthz`, checks the SPA and verifies durable files are created;
- publication workflow preparation targets Linux `amd64` and `arm64`.

Release-grade ARM64 hardware validation and upgrade/migration policy are still pending.

## Deployment families

- [`docker/`](docker/) — implemented alpha container image and local/self-hosted Compose runtime.
- [`umbrel/`](umbrel/) — planned Umbrel application packaging built on the same image/runtime contract.

Deployment code must not become a second FoxForge implementation. Docker and Umbrel must package the same backend, API and compiled frontend behavior. Vendor/network behavior belongs in FoxForge runtime/adapters, not in platform-specific forks.

## Remaining release work

Before calling deployment production-ready, FoxForge still needs:

1. immutable release/tag image publication and digest policy;
2. representative ARM64 runtime smoke testing;
3. persisted-state upgrade/migration rules;
4. user-facing runtime configuration documentation;
5. Umbrel App Store packaging and App Proxy integration;
6. end-to-end Umbrel validation using the same FoxForge application image.
