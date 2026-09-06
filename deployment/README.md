# FoxForge deployment

FoxForge ships one application behavior across generic Docker and Umbrel packaging. Deployment code must not become a platform-specific fork of printer, queue or inventory logic.

## Current deployment identities

The latest semantic release is `v0.1.0-alpha.4.3`.

The current Umbrel package is a **Pre-Alpha 5 validation candidate**, not final Alpha 5:

```text
package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.3
source: 37d1cbed8f73d62acdc1994545bc2f5ee57e816a
image: ghcr.io/mikefox303/foxforge:sha-37d1cbe@sha256:4e652006212db2527804abbd478b7b64fde127414b1dbe22703854280ccfce82
Store commit: cc6010fdff4823b671a92be3b307155f26db85bc
```

Candidate 3 replaces candidate 2 as the current physical-test target because the material-routing, queue and Bambu native print-command behavior changed after candidate 2.

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
- Bambu discovery is an explicit, bounded scan of a user-selected RFC1918 IPv4 subnet and produces candidates only;
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
