# Umbrel deployment

FoxForge is packaged as `my3d-foxforge` in the companion `MikeFox303/umbrel-3d-printing-store` Community App Store.

## Current package status

The latest semantic release remains `v0.1.0-alpha.4.3`. Candidate 5 is historical and retired for final Alpha 5 acceptance. Candidate 6 is still being stabilized and **has not yet been frozen or published**, so no Candidate 6 package version/source/digest should be invented before C6-11.

> [!IMPORTANT]
> Candidate 6 physical validation must use one exact source/image/Umbrel package/Store identity created by C6-11. Editing the installed package definition after evidence starts invalidates that evidence.

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

## Candidate 6 filament-accounting mode

The FoxForge runtime default is:

```text
FOXFORGE_FILAMENT_ACCOUNTING_MODE=disabled
```

For the controlled Candidate 6 Bambu accounting acceptance, the immutable Candidate 6 Umbrel package should intentionally set:

```text
FOXFORGE_FILAMENT_ACCOUNTING_MODE=bambu-validation
```

when C6-11 is published. That mode applies the common pre-dispatch reservation/assignment/capacity gate only to printers configured with `adapter_kind == "bambu"`. It does not enable Moonraker/Klipper accounting and does not derive consumed grams from progress.

The chosen value is part of the immutable Candidate 6 package contract. Do **not** install a `disabled` package, edit Compose manually to `bambu-validation`, and then claim the original package identity for accounting evidence. If the package needs a different mode, publish a new immutable candidate/package identity first.

Validation must record `/api/v1/diagnostics/persistence` and confirm the active `filamentAccounting.mode` plus `enforcedAdapterKinds`.

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

Pre-Alpha 5 uses conservative Bambu discovery:

- FoxForge may suggest bounded private RFC1918 networks visible from the server/container;
- the operator explicitly selects a suggestion or enters the private CIDR manually;
- scanning is limited to `/22` or smaller networks;
- a candidate must expose the expected Bambu MQTT and FTPS service ports;
- SSDP metadata may fill serial/name/model;
- discovery never persists a printer by itself;
- normal authenticated test-before-save must still succeed.

Manual Bambu entry remains available and is the fallback when discovery cannot see the printer from the deployment network namespace.

## Candidate 6 publication and install

Before an install can count as Candidate 6 physical evidence:

1. C6-10 must pass on clean FoxForge `main`;
2. C6-11 must publish the exact multi-arch image/digest and matching Umbrel package;
3. the companion Store package must pin that exact immutable image;
4. the package definition must already contain the intended accounting mode for the validation run;
5. the runbook must record the exact source/image/package/Store identities.

Then:

1. add/refresh `https://github.com/MikeFox303/umbrel-3d-printing-store` as a Community App Store;
2. confirm the exact Candidate 6 package is offered;
3. install/update without manual Compose/container modifications;
4. confirm the app starts and `/healthz` succeeds;
5. obtain the app password from the Umbrel UI and unlock FoxForge writes;
6. follow the exact [Pre-Alpha 5 Bambu physical-validation runbook](../../docs/testing/pre-alpha-5-bambu-physical-validation.md).

Successful package CI or install alone is not physical X2D acceptance.

## Persistence and upgrades

Persistent `/data` includes application configuration, SQLite state, SecretStore data and staged artifacts. Back up the complete directory before early-alpha upgrades and treat it as sensitive.

A changed source commit, image digest or package definition is a new physical-test target. Evidence from an earlier candidate may be retained historically but must not be silently carried forward.

## Remaining gate

Final Alpha 5 remains blocked on exact Candidate 6 Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro acceptance, including setup negative paths, safe update rollback, partial X2D status, reconnect recovery, thermal/material topology, immutable 3MF routing, provider-scoped filament accounting, exactly-one project upload/start and guarded job control.
