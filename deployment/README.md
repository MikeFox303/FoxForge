# FoxForge deployment

FoxForge ships one application behavior across generic Docker and Umbrel packaging. Deployment code must not become a platform-specific fork of printer, queue or inventory logic.

## Current deployment identities

The latest semantic release is `v0.1.0-alpha.4.3`.

The current Umbrel package is a **Pre-Alpha 5 validation candidate**, not final Alpha 5:

```text
package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.4
source: c11f7145b4354aa79c8f0fad223648240e652bac
image: ghcr.io/mikefox303/foxforge:sha-c11f714@sha256:75d656bafcafb4e0e566548f6cca941244d29fef1bbc5be98e425f375246056a
```

## Runtime model

- one multi-stage image builds the React frontend and Python backend;
- one `aiohttp` process serves the compiled SPA, `/api/v1`, `/api/v1/events` and `/healthz`;
- persistent application data lives under `/data`;
- printer credentials are stored behind `SecretStore`;
- print artifacts live under `/data/artifacts`;
- steady-state container execution is non-root;
- Docker and Umbrel use the same application image/runtime contract.

## Write authentication

Protected writes require `FOXFORGE_COMMAND_TOKEN`.

For standalone Docker, configure a high-entropy token and enter the same value in **Operator Access / Unlock writes**. Omitting the token is deliberate read-only mode for protected commands.

The browser retains the operator credential only in memory for the current tab. FoxForge does not store it in URLs, `localStorage`, `sessionStorage`, public DTOs or logs.

`FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is rejected by the production runtime. Reverse-proxy headers or a private container network are not FoxForge application authentication. See [ADR 0005](../docs/adr/0005-browser-command-authentication.md).

### Umbrel

The companion package maps:

```text
FOXFORGE_COMMAND_TOKEN=${APP_PASSWORD}
```

Umbrel exposes the app password through its UI, so the operator can unlock FoxForge writes without terminal lookup. App Proxy remains a separate defense-in-depth boundary; it does not become a FoxForge principal.

## Printer networking

Current printer transports use deployment-to-printer LAN connectivity:

- Bambu MQTT/TLS and FTPS use configured/discovered printer addresses;
- Moonraker uses the configured base URL;
- Bambu discovery can suggest server-visible private RFC1918 networks and performs an explicit bounded scan of the selected/manual CIDR; results remain candidates only;
- discovered Bambu candidates still must pass normal authenticated test-before-save before configuration is persisted.

No Docker socket, privileged mode or `network_mode: host` is required by the current package. Real bridge/container reachability to the printer LAN remains part of physical validation. Broader network features such as Virtual Printer require separate design and evidence.

## Deployment families

- [`docker/`](docker/) — standalone self-hosted Compose/runtime.
- [`umbrel/`](umbrel/) — Community App packaging and current Pre-Alpha 5 validation candidate.

## Upgrade and persistence

Early-alpha persistence is migration-owned but pre-stable. Back up the complete `/data` directory before upgrades and treat backups as credential-bearing data.

Source changes on `main` do not mutate an already published immutable semantic release or validation candidate. A changed physical-test target requires a new digest-pinned package and fresh evidence for the affected path.

## Production-readiness gate

FoxForge still requires representative physical evidence for Raspberry Pi 5/Umbrel, real Bambu X2D/AMS 2 Pro behavior and Moonraker/OpenKE behavior before production claims.

For the active Bambu milestone use [`../docs/testing/pre-alpha-5-bambu-physical-validation.md`](../docs/testing/pre-alpha-5-bambu-physical-validation.md). Generic evidence rules are in [`../docs/testing/physical-validation-runbook.md`](../docs/testing/physical-validation-runbook.md).
