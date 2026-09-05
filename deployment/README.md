# FoxForge deployment

Deployment assets live separately from backend and frontend source code, but package the same FoxForge application.

## Current status

FoxForge deployment is a runnable/installable alpha implementation:

- one multi-stage image builds the React frontend and Python backend;
- one `aiohttp` runtime serves the compiled SPA and `/api/v1`;
- standalone Compose configuration is available under `docker/`;
- application state is persisted outside the image under `/data`;
- first start creates current schema state (`config.json` schema 2 and SQLite `user_version` 1);
- printer credentials are stored behind the `SecretStore` boundary;
- staged print artifacts are persisted under `/data/artifacts`;
- the container prepares mounted-data permissions before dropping to a non-root steady-state user;
- CI builds and starts the production image and validates health, browser behavior, persistence and deployment authentication contracts;
- `v0.1.0-alpha.4` is published as an immutable Linux `amd64` + `arm64` image with SBOM/provenance metadata;
- the companion Umbrel Community App update pins the exact `alpha.4` multi-architecture digest.

Published `alpha.4` image:

```text
ghcr.io/mikefox303/foxforge:0.1.0-alpha.4@sha256:0b0d96e5243db82ad3349bbc1c96243cbc6288c27eb716ff80512eb925b9fef4
```

Representative Raspberry Pi 5 hardware validation, physical printer-network validation and stable release-to-release deployment evidence are still pending.

## Browser/API write authentication

FoxForge write commands are fail-closed and require `FOXFORGE_COMMAND_TOKEN`. Read-only operation remains supported when the token is unset.

For standalone Docker:

1. copy `deployment/docker/.env.example` to `deployment/docker/.env`;
2. generate a high-entropy token of at least 32 visible ASCII characters;
3. set `FOXFORGE_COMMAND_TOKEN` in that `.env` file;
4. start Compose;
5. enter the same token in **Unlock writes** in the FoxForge browser UI when write access is needed.

The browser keeps the token only in memory for the current tab. FoxForge does not place it in URLs, `localStorage`, `sessionStorage`, public API DTOs or logs. A 401 response or explicit **Lock** clears the in-memory credential.

`FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is deliberately rejected by the production runtime. A reverse proxy, private Docker network or forwarded header is not by itself proof of application authentication. Tokenless proxy bootstrap requires a future cryptographically authenticated contract and representative deployment tests; see [ADR 0005](../docs/adr/0005-browser-command-authentication.md).

The production-container contract is executable in `.github/workflows/deployment-auth.yml` and documented in [Deployment authentication acceptance](../docs/testing/deployment-auth-contract.md). It verifies intentionally read-only and explicit-token write-enabled runtimes, invalid bearer rejection, tokenless session rejection and fail-closed startup for the unsafe trusted-browser flag.

## Umbrel authentication status

The `v0.1.0-alpha.4` Umbrel package is configured as **write-enabled** without treating Umbrel App Proxy as a FoxForge principal.

The package maps Umbrel's per-app `APP_PASSWORD` to:

```text
FOXFORGE_COMMAND_TOKEN=${APP_PASSWORD}
```

The operator opens FoxForge through Umbrel and enters that same app password in **Unlock writes**. The credential remains memory-only in the browser tab and is sent as the FoxForge Bearer credential for protected commands.

This preserves two independent boundaries:

- **Umbrel App Proxy** — authenticated access to the application surface;
- **FoxForge command authorization** — explicit `FOXFORGE_COMMAND_TOKEN` required for protected writes.

Direct tokenless backend access remains fail-closed. Tokenless `/api/v1/operator-session` remains disabled, and `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` remains unsupported.

The companion Store package contract verifies the exact image/digest, the `APP_PASSWORD` → `FOXFORGE_COMMAND_TOKEN` mapping, Compose rendering, anonymous image pull and runtime startup on Linux `amd64` and `arm64`.

That software/package evidence does **not** by itself resolve AUD-003. Real Raspberry Pi 5/Umbrel installation, proxy/write behavior, direct-backend fail-closed behavior, printer-network reachability, upgrade and SSE reconnect/resync evidence are still required.

See [`umbrel/README.md`](umbrel/README.md) for the package-specific contract and validation boundary.

## Deployment families

- [`docker/`](docker/) — implemented alpha container image and local/self-hosted Compose runtime; explicit-token writes and tokenless read-only mode are covered by production-container CI.
- [`umbrel/`](umbrel/) — Community App packaging built on the same release image/runtime; `alpha.4` is configured with an explicit FoxForge application credential path using Umbrel `APP_PASSWORD`.

Deployment code must not become a second FoxForge implementation. Docker and Umbrel package the same backend, API and compiled frontend behavior. Vendor/network behavior belongs in FoxForge runtime/adapters, not in platform-specific forks.

## Current release contract

The published deployment line is `v0.1.0-alpha.4`.

Release publication is guarded by:

- release identity/version consistency;
- frozen dependency installation;
- backend lint/tests;
- frontend typecheck/tests/build;
- unified image build and live health/SPA/persistence smoke;
- immutable tag uniqueness checks;
- Linux `amd64` + `arm64` publication with SBOM/provenance;
- GitHub pre-release creation only after the preceding gates succeed.

Changes merged after a release are not delivered through floating semantic tags; they require another guarded FoxForge release and, for Umbrel, a corresponding Store package update.

Persistent `/data` contains runtime configuration, SQLite state, secrets and staged print artifacts. Back up the complete directory before early-alpha upgrades and treat backups as credential-bearing data.

## Remaining production-readiness work

Before calling deployment production-ready, FoxForge still needs:

1. representative Raspberry Pi 5 / physical ARM64 install, restart and persistence validation;
2. real Umbrel App Proxy/browser write-path evidence using the published package plus direct-backend fail-closed verification;
3. real Bambu X2D and Moonraker/OpenKE reachability from Docker/Umbrel network environments;
4. end-to-end physical upload/start/control/lifecycle/reconciliation validation;
5. validation of upgrade behavior between published FoxForge/Umbrel package versions;
6. representative SSE reconnect/resync behavior through the deployed proxy path;
7. separate network design and testing before enabling discovery, Virtual Printer or features requiring broader LAN access.
