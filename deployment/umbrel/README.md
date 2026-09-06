# Umbrel deployment

FoxForge is packaged as `my3d-foxforge` in the companion `MikeFox303/umbrel-3d-printing-store` Community App Store.

## Current package

The Store currently carries the **third Pre-Alpha 5 physical-validation candidate**:

```text
package version: 0.1.0-alpha.4.3-umbrel.3
package role: pre-alpha-5-validation-candidate
base semantic release: 0.1.0-alpha.4.3
target semantic release: 0.1.0-alpha.5
source commit: 37d1cbed8f73d62acdc1994545bc2f5ee57e816a
Store commit: cc6010fdff4823b671a92be3b307155f26db85bc
image: ghcr.io/mikefox303/foxforge:sha-37d1cbe@sha256:4e652006212db2527804abbd478b7b64fde127414b1dbe22703854280ccfce82
Umbrel app port: 8283
internal server port: 8000
```

Candidate 3 replaces Candidate 2 as the current physical target because the material-routing compiler, queue routing integration and Bambu native nozzle-mapping path changed after Candidate 2.

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

The Candidate 3 Store gates verified the package contract plus anonymous public runtime startup on both `linux/amd64` and `linux/arm64` using the exact digest above.

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

## Safe routed Bambu print path

Candidate 3 adds the software gate required before the first real X2D print:

- immutable staged `.3mf` print-plan/material-requirement inspection;
- explicit physical source bindings rather than material/color auto-selection;
- vendor-neutral source→toolhead routing compilation;
- queue persistence of compiler-owned toolhead bindings;
- final Bambu source-presence/topology/toolhead revalidation from one native snapshot;
- `project_file` `ams_mapping` / `ams_mapping2` / `nozzle_mapping` derived only from the proven route;
- external source IDs 254/255 retained in `ams_mapping2` while flat `ams_mapping` uses `-1`;
- ambiguous or stale routing blocks before transport instead of guessing a nozzle.

These are software guarantees only until the Candidate 3 X2D physical matrix is completed.

## Install for current physical validation

1. Add/refresh `https://github.com/MikeFox303/umbrel-3d-printing-store` as a Community App Store.
2. Confirm FoxForge version `0.1.0-alpha.4.3-umbrel.3` is offered.
3. Install/update FoxForge without manual Compose/container modifications.
4. Confirm the app starts and `/healthz` succeeds.
5. Obtain the app password from the Umbrel UI and unlock FoxForge writes.
6. Follow the exact [Pre-Alpha 5 Bambu physical-validation runbook](../../docs/testing/pre-alpha-5-bambu-physical-validation.md).

Do not treat successful package CI or install alone as proof that X2D print/control workflows are production-ready.

## Persistence and upgrades

Persistent `/data` includes application configuration, SQLite state, SecretStore data and staged artifacts. Back up the complete directory before early-alpha upgrades and treat it as sensitive.

A changed source commit/image digest is a new physical-test target. Evidence from an earlier candidate may be retained historically but must not be silently carried forward to a changed image.

## Remaining gate

Final Alpha 5 remains blocked on real Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro acceptance, including setup negative paths, safe update rollback, reconnect recovery, live AMS/external-source state, explicit `.3mf` material routing, real project upload/start and guarded job control.
