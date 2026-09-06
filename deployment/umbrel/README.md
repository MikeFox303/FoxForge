# Umbrel deployment

FoxForge is packaged as `my3d-foxforge` in the companion `MikeFox303/umbrel-3d-printing-store` Community App Store.

## Current package

The Store currently carries the **second Pre-Alpha 5 physical-validation candidate**:

```text
package version: 0.1.0-alpha.4.3-umbrel.2
package role: pre-alpha-5-validation-candidate
base semantic release: 0.1.0-alpha.4.3
target semantic release: 0.1.0-alpha.5
source commit: 37b253f385c19451c7ea075a4a4d12378cf17cf2
Store commit: 1d7d78d7a0f3c36805071dd6d8078033c59672ac
image: ghcr.io/mikefox303/foxforge:sha-37b253f@sha256:e550c8026ed6ec80e973d91fe6d96cc1474d537ca87de7875ec54f4a03aaaa4f
Umbrel app port: 8283
internal server port: 8000
```

> [!IMPORTANT]
> This is an installable validation candidate, **not** final `v0.1.0-alpha.5`.

## Operator authentication

Umbrel supplies a unique per-app `APP_PASSWORD`; the FoxForge package maps it to:

```text
FOXFORGE_COMMAND_TOKEN=${APP_PASSWORD}
```

The package also exposes the FoxForge app password through the Umbrel UI so normal operators do not need a terminal command to discover the credential.

To use protected actions:

1. open FoxForge through Umbrel;
2. open **Operator Access / Unlock writes**;
3. enter the FoxForge app password shown by Umbrel;
4. use protected commands in the current tab;
5. reload/close the tab or choose Lock to clear the browser-held credential.

App Proxy remains defense in depth and is not a FoxForge application principal. Direct protected writes still require the correct Bearer credential. Tokenless `/api/v1/operator-session` remains disabled, and `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` remains unsupported.

## Packaging model

The package uses:

- ordinary Docker bridge networking;
- no host networking;
- no privileged mode or extra Linux capabilities;
- no Docker socket access;
- `${APP_DATA_DIR}/data:/data` persistence;
- `/healthz` container health check;
- the same FoxForge application image used by the project runtime.

## Printer networking and discovery

Bambu and Moonraker communication occurs from the FoxForge container to printer addresses on the LAN.

Pre-Alpha 5 adds conservative Bambu discovery:

- the operator selects a private RFC1918 IPv4 subnet;
- scanning is limited to `/22` or smaller networks;
- a candidate must expose the expected Bambu MQTT and FTPS service ports;
- SSDP metadata may fill serial/name/model;
- discovery never persists a printer by itself;
- normal authenticated test-before-save must still succeed.

Manual Bambu entry remains available and is the fallback when discovery cannot see the printer from the deployment network namespace.

## Install for current physical validation

1. Add/refresh `https://github.com/MikeFox303/umbrel-3d-printing-store` as a Community App Store.
2. Confirm FoxForge version `0.1.0-alpha.4.3-umbrel.2` is offered.
3. Install/update FoxForge without manual Compose/container modifications.
4. Confirm the app starts and `/healthz` succeeds.
5. Obtain the app password from the Umbrel UI and unlock FoxForge writes.
6. Follow the exact [Pre-Alpha 5 Bambu physical-validation runbook](../../docs/testing/pre-alpha-5-bambu-physical-validation.md).

Do not treat successful package CI or install alone as proof that X2D print/control workflows are production-ready.

## Persistence and upgrades

Persistent `/data` includes application configuration, SQLite state, SecretStore data and staged artifacts. Back up the complete directory before early-alpha upgrades and treat it as sensitive.

A changed source commit/image digest is a new physical-test target. Evidence from an earlier candidate may be retained historically but must not be silently carried forward to a changed image.

## Remaining gate

Final Alpha 5 remains blocked on real Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro acceptance, including setup negative paths, safe update rollback, reconnect recovery, live AMS state, real project upload/start and guarded job control.
