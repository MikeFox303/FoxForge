# Umbrel deployment

FoxForge is packaged as `my3d-foxforge` in the companion `MikeFox303/umbrel-3d-printing-store` Community App Store.

## Current package status

The latest semantic release remains `v0.1.0-alpha.4.3`. Final `v0.1.0-alpha.5` is unpublished.

The active Pre-Alpha 5 physical-validation package is **Candidate 7**:

```text
FoxForge application source: 4f769ca89d466d2cbe41360848b6343ec5a8eb36
image tag: ghcr.io/mikefox303/foxforge:sha-4f769ca
OCI digest: sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
exact image: ghcr.io/mikefox303/foxforge:sha-4f769ca@sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.7
Umbrel Store commit: 6e69e4005ae9529eeee5c376c8769393b056ee0d
```

Candidate 5 and Candidate 6 are historical. Candidate 6 failed the real X2D Add Printer physical gate after UI Verify could succeed; PR #184 fixed the Add/MQTT connection lifecycle, requiring Candidate 7 as the new immutable target.

> [!IMPORTANT]
> Candidate 7 physical validation must use the exact source/image/Umbrel package/Store identity above. Editing the installed package definition after evidence starts invalidates that evidence and requires Candidate 8.

## Operator authentication

Umbrel supplies a unique per-app `APP_PASSWORD`; the FoxForge package maps it to:

```text
FOXFORGE_COMMAND_TOKEN=${APP_PASSWORD}
```

The package exposes the FoxForge app password through the Umbrel UI so normal operators do not need a terminal command to discover the credential.

To use protected actions:

1. open FoxForge through Umbrel;
2. open **Operator Access / Unlock writes**;
3. enter the FoxForge app password shown by Umbrel;
4. use protected commands in the current tab;
5. reload/close the tab or choose Lock to clear the browser-held credential.

App Proxy remains defense in depth and is not a FoxForge application principal. Direct protected writes still require the correct Bearer credential. Tokenless `/api/v1/operator-session` remains disabled, and `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` remains unsupported.

## Candidate 7 filament-accounting mode

The generic FoxForge runtime default is:

```text
FOXFORGE_FILAMENT_ACCOUNTING_MODE=disabled
```

The published Candidate 7 Umbrel package intentionally sets:

```text
FOXFORGE_FILAMENT_ACCOUNTING_MODE=bambu-validation
```

That mode applies the common pre-dispatch reservation/assignment/capacity gate only to printers configured with `adapter_kind == "bambu"`. It does not enable Moonraker/Klipper accounting and does not derive consumed grams from progress.

The chosen value is part of the immutable Candidate 7 package contract. Do **not** edit Compose manually and then claim the original package identity for accounting evidence. If the package needs a different mode, publish a new immutable candidate/package identity first.

Validation must record `/api/v1/diagnostics/persistence` and confirm:

```json
{
  "mode": "bambu-validation",
  "enforcedAdapterKinds": ["bambu"]
}
```

## Packaging model

The Candidate 7 package uses:

- ordinary Docker bridge networking;
- no host networking;
- no privileged mode or extra Linux capabilities;
- no Docker socket access;
- `${APP_DATA_DIR}/data:/data` persistence;
- `/healthz` container health check;
- the same immutable FoxForge application image published for Candidate 7.

The companion Store package/runtime CI passed on both `linux/amd64` and `linux/arm64` before Store commit `6e69e4005ae9529eeee5c376c8769393b056ee0d` was merged.

## Printer networking and discovery

Bambu and Moonraker communication occurs from the FoxForge container to printer addresses on the LAN.

Pre-Alpha 5 uses conservative Bambu discovery:

- FoxForge may suggest bounded private RFC1918 networks visible from the server/container;
- the operator explicitly selects a suggestion or enters the private CIDR manually;
- scanning is limited to `/22` or smaller networks;
- a candidate must expose the expected Bambu MQTT and FTPS service ports;
- SSDP metadata may fill serial/name/model;
- discovery never persists a printer by itself;
- normal authenticated exact-payload Verify must still succeed.

Candidate 7's Add path then uses the live fleet adapter as the single backend-authoritative connection before durable config/secrets are accepted. Bambu MQTT sessions use short per-session client IDs, so separate Verify/Add/reconnect sessions do not deliberately reuse one serial-derived broker identity. Update Printer keeps its separate preflight/rollback path because it protects an already-known-good configuration.

Manual Bambu entry remains available and is the fallback when discovery cannot see the printer from the deployment network namespace.

## Candidate 7 install and physical validation

To begin the authorized Candidate 7 physical gate:

1. add/refresh `https://github.com/MikeFox303/umbrel-3d-printing-store` as a Community App Store;
2. confirm **`my3d-foxforge 0.1.0-alpha.4.3-umbrel.7`** is offered;
3. install/update without manual Compose/container modifications;
4. confirm the app starts and `/healthz` succeeds;
5. obtain the app password from the Umbrel UI and unlock FoxForge writes;
6. record the source, OCI digest, package version and Store commit shown above;
7. follow the exact [Pre-Alpha 5 Bambu physical-validation runbook](../../docs/testing/pre-alpha-5-bambu-physical-validation.md).

The first required real-device regression is the Candidate 6 blocker:

```text
X2D exact payload → Verify succeeds → Add/Save immediately → persists and stays connected
```

`internal_adapter_error` must not recur. A successful package install alone is not physical X2D acceptance, and a physical print remains blocked until all no-print sections pass.

## Persistence and upgrades

Persistent `/data` includes application configuration, SQLite state, SecretStore data and staged artifacts. Back up the complete directory before early-alpha upgrades and treat it as sensitive.

A changed application source, image digest or package definition is a new physical-test target. Evidence from an earlier candidate may be retained historically but must not be silently carried forward. Documentation-only status/evidence commits after the Candidate 7 freeze are not application identity.

## Remaining gate

Final Alpha 5 remains blocked on exact Candidate 7 Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro acceptance, including the Verify→Add regression, setup negative paths, safe Update rollback, partial X2D status, reconnect recovery, thermal/material topology, immutable 3MF routing, provider-scoped filament accounting, exactly-one project upload/start and guarded job control.
