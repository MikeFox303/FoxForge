# FoxForge deployment

FoxForge ships one application behavior across generic Docker and Umbrel packaging. Deployment code must not become a platform-specific fork of printer, queue, inventory or accounting logic.

## Current deployment identities

The latest semantic release remains `v0.1.0-alpha.4.3`; final `v0.1.0-alpha.5` is unpublished.

The active Pre-Alpha 5 physical-validation target is Candidate 7:

```text
application source: 4f769ca89d466d2cbe41360848b6343ec5a8eb36
image: ghcr.io/mikefox303/foxforge:sha-4f769ca@sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
Umbrel package: 0.1.0-alpha.4.3-umbrel.7
Umbrel Store commit: 6e69e4005ae9529eeee5c376c8769393b056ee0d
```

Candidate 5 and Candidate 6 are historical and must not be used as Candidate 7 evidence. Candidate 6 specifically failed the real X2D Add Printer physical path after UI Verify; PR #184 fixed the Add/MQTT session lifecycle and required Candidate 7 as a new immutable target.

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

## Filament-accounting enforcement

The runtime supports a closed accounting-mode contract through:

```text
FOXFORGE_FILAMENT_ACCOUNTING_MODE=disabled
```

Supported values:

- `disabled` — default for ordinary deployments;
- `bambu-validation` — controlled Candidate 7 mode that applies the common pre-dispatch reservation/assignment/capacity gate only to printers configured with `adapter_kind == "bambu"`.

Unsupported values fail startup. Moonraker/Klipper is not enabled by the Bambu mode. The active mode is exposed in `/api/v1/diagnostics/persistence` for validation evidence.

Generic Docker remains `disabled` by default. The immutable Candidate 7 Umbrel package already contains `bambu-validation`; do not edit the installed package and then reuse the same evidence identity. A required package-definition change means a new candidate.

## Printer networking

Current printer transports use deployment-to-printer LAN connectivity:

- Bambu MQTT/TLS and FTPS use configured/discovered printer addresses;
- Bambu MQTT connections use a short per-session client ID so separate Verify/Add/reconnect sessions do not deliberately reuse one broker identity;
- Add Printer uses the exact live fleet adapter as the single backend-authoritative connection before durable persistence;
- Update Printer keeps a separate verification/rollback path to protect a known-good configuration;
- Moonraker uses the configured base URL;
- Bambu discovery can suggest server-visible private RFC1918 networks and performs an explicit bounded scan of the selected/manual CIDR; results remain candidates only;
- discovered Bambu candidates still must pass normal authenticated exact-payload Verify before Save.

No Docker socket, privileged mode or `network_mode: host` is required by the current package. Real bridge/container reachability to the printer LAN remains part of physical validation. Broader network features such as Virtual Printer require separate design and evidence.

## Deployment families

- [`docker/`](docker/) — standalone self-hosted Compose/runtime.
- [`umbrel/`](umbrel/) — Community App packaging contract used by Candidate publication.

## Upgrade and persistence

Early-alpha persistence is migration-owned but pre-stable. Back up the complete `/data` directory before upgrades and treat backups as credential-bearing data.

Source changes on `main` do not mutate an already published immutable semantic release or validation candidate. Documentation-only status/evidence commits after a candidate freeze are not application identity. A changed application/image/package physical-test target requires a new digest-pinned package and fresh evidence for the affected path.

## Production-readiness gate

FoxForge still requires representative physical evidence for Raspberry Pi 5/Umbrel, real Bambu X2D/AMS 2 Pro behavior and Moonraker/OpenKE behavior before production claims.

Candidate 7 publication/package CI is green, so the active Bambu no-print gate is authorized. The first required regression is real X2D **Verify → Add** without Candidate 6's `internal_adapter_error`, followed by Update rollback, reconnect/network-loss diagnostics, partial-status handling, thermal/material topology and accounting mode. A physical print remains blocked until the no-print gate passes.

For the active Bambu milestone use [`../docs/testing/pre-alpha-5-bambu-physical-validation.md`](../docs/testing/pre-alpha-5-bambu-physical-validation.md). Generic evidence rules are in [`../docs/testing/physical-validation-runbook.md`](../docs/testing/physical-validation-runbook.md).
