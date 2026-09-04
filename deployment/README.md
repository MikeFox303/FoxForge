# FoxForge deployment

Deployment assets live separately from backend and frontend source code, but package the same FoxForge application.

## Current status

FoxForge deployment is a runnable/installable alpha implementation:

- one multi-stage image builds the React frontend and Python backend;
- one `aiohttp` runtime serves the compiled SPA and `/api/v1`;
- standalone Compose configuration is available under `docker/`;
- application state is persisted outside the image under `/data`;
- first start creates safe local configuration/database state;
- staged print artifacts are persisted under `/data/artifacts`;
- the container prepares mounted data permissions before dropping to a non-root steady-state user;
- CI builds and starts the container, checks `/healthz`, checks the SPA and verifies durable files are created;
- `v0.1.0-alpha.3` is published as an immutable Linux `amd64` + `arm64` image with SBOM/provenance metadata;
- anonymous runtime smoke passes for both published architectures;
- the companion Umbrel Community App packages the same immutable FoxForge alpha.3 image behind Umbrel App Proxy.

Representative Raspberry Pi 5 hardware validation, physical printer-network validation and stable upgrade/migration guarantees are still pending.

## Deployment families

- [`docker/`](docker/) — implemented alpha container image and local/self-hosted Compose runtime.
- [`umbrel/`](umbrel/) — implemented Community App packaging built on the same image/runtime contract and currently pinned to the immutable alpha.3 multi-architecture digest.

Deployment code must not become a second FoxForge implementation. Docker and Umbrel package the same backend, API and compiled frontend behavior. Vendor/network behavior belongs in FoxForge runtime/adapters, not in platform-specific forks.

## Current release contract

The published deployment line is `v0.1.0-alpha.3`.

Release publication is guarded by backend/frontend validation, unified image smoke, multi-architecture publication and immutable version/digest pinning. Changes merged after a release are not delivered through floating tags; they require another guarded FoxForge release and, for Umbrel, a corresponding Store package update.

Persistent `/data` currently contains runtime configuration, SQLite state and staged print artifacts. Persistence compatibility remains pre-stable, so operators should back up application data before upgrading between early alpha releases.

## Remaining production-readiness work

Before calling deployment production-ready, FoxForge still needs:

1. representative Raspberry Pi 5 / physical ARM64 install, restart and persistence validation;
2. real Bambu X2D and Moonraker/OpenKE reachability from Docker/Umbrel network environments;
3. end-to-end physical upload/start/lifecycle/reconciliation validation;
4. explicit persisted-state migration/compatibility policy for later releases;
5. validation of upgrade behavior between published FoxForge/Umbrel package versions;
6. separate network design and testing before enabling discovery, Virtual Printer or features requiring broader LAN access.
