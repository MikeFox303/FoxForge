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
- CI builds and starts the production image and validates health, browser behavior, persistence and deployment authentication contracts;
- `v0.1.0-alpha.3` is published as an immutable Linux `amd64` + `arm64` image with SBOM/provenance metadata;
- the companion Umbrel Community App remains pinned to that historical immutable alpha.3 image.

Representative Raspberry Pi 5 hardware validation, physical printer-network validation and stable release-to-release deployment evidence are still pending.

## Browser/API write authentication

FoxForge write commands are fail-closed and require `FOXFORGE_COMMAND_TOKEN`. Read-only operation remains supported when the token is unset.

For standalone Docker:

1. copy `deployment/docker/.env.example` to `deployment/docker/.env`;
2. generate a high-entropy token of at least 32 visible ASCII characters;
3. set `FOXFORGE_COMMAND_TOKEN` in that `.env` file;
4. start Compose;
5. enter the same token in the **Operator access** control in the FoxForge browser UI when write access is needed.

The browser keeps the token only in memory for the current tab. FoxForge does not place it in URLs, `localStorage`, `sessionStorage`, public API DTOs or logs. A 401 response or explicit **Lock** clears the in-memory credential.

`FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is deliberately rejected by the production runtime. A reverse proxy, private Docker network or forwarded header is not by itself proof of application authentication. Tokenless proxy bootstrap requires a future cryptographically authenticated contract and representative deployment tests; see [ADR 0005](../docs/adr/0005-browser-command-authentication.md).

The production-container contract is executable in `.github/workflows/deployment-auth.yml` and documented in [Deployment authentication acceptance](../docs/testing/deployment-auth-contract.md). It verifies both intentionally read-only and explicit-token write-enabled runtimes, invalid bearer rejection, tokenless session rejection and fail-closed startup for the unsafe trusted-browser flag.

## Umbrel authentication status

The immutable `v0.1.0-alpha.3` Umbrel package is historical and is not rewritten. Its Store Compose does not configure `FOXFORGE_COMMAND_TOKEN` or another ADR-0005-compatible application bootstrap. Therefore FoxForge does **not** claim that historical package as a validated write-capable deployment.

Umbrel App Proxy remains defense in depth, but it is not a FoxForge application principal. A future Umbrel package must either:

- configure and test an ADR-0005-compatible FoxForge credential/bootstrap; or
- deliberately expose protected writes as unavailable/read-only with truthful UI/documentation.

See [`umbrel/README.md`](umbrel/README.md) for the exact historical-package limitations and the evidence required before a future write-capable package is published.

## Deployment families

- [`docker/`](docker/) — implemented alpha container image and local/self-hosted Compose runtime; explicit-token writes and tokenless read-only mode are covered by production-container CI.
- [`umbrel/`](umbrel/) — Community App packaging built on the same image/runtime concept; currently pinned to immutable alpha.3 and not claimed as validated for protected browser writes.

Deployment code must not become a second FoxForge implementation. Docker and Umbrel package the same backend, API and compiled frontend behavior. Vendor/network behavior belongs in FoxForge runtime/adapters, not in platform-specific forks.

## Current release contract

The published deployment line is `v0.1.0-alpha.3`.

Release publication is guarded by backend/frontend validation, unified image smoke, multi-architecture publication and immutable version/digest pinning. Changes merged after a release are not delivered through floating tags; they require another guarded FoxForge release and, for Umbrel, a corresponding Store package update.

Persistent `/data` contains runtime configuration, SQLite state and staged print artifacts. Current source also has explicit migration/version ownership and a `SecretStore` boundary, but those post-alpha.3 changes require a later guarded release before installed alpha.3 users receive them.

## Remaining production-readiness work

Before calling deployment production-ready, FoxForge still needs:

1. representative Raspberry Pi 5 / physical ARM64 install, restart and persistence validation;
2. an exact future Umbrel package whose write/read-only authentication behavior matches ADR 0005 and the deployment acceptance matrix;
3. real Bambu X2D and Moonraker/OpenKE reachability from Docker/Umbrel network environments;
4. end-to-end physical upload/start/control/lifecycle/reconciliation validation;
5. validation of upgrade behavior between published FoxForge/Umbrel package versions;
6. separate network design and testing before enabling discovery, Virtual Printer or features requiring broader LAN access.
