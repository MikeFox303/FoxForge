# Umbrel deployment

FoxForge is packaged as `my3d-foxforge` in the companion [`MikeFox303/umbrel-3d-printing-store`](https://github.com/MikeFox303/umbrel-3d-printing-store) Community App Store.

## Current package status

The latest semantic FoxForge release remains `v0.1.0-alpha.4.3`; final `v0.1.0-alpha.5` is **not published**.

Pre-Alpha 5 physical-validation **Candidate 6 is published and installable** with one frozen application/package identity:

```text
FoxForge application source: 78ace6f7b7412aa0d3fc58bed095aecdf9920f94
image tag: ghcr.io/mikefox303/foxforge:sha-78ace6f
OCI digest: sha256:b01f1d44199a4413167ee2369c0dfbcafa602312442772d27de18e04c24ed0eb
exact image: ghcr.io/mikefox303/foxforge:sha-78ace6f@sha256:b01f1d44199a4413167ee2369c0dfbcafa602312442772d27de18e04c24ed0eb
Umbrel package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.6
Umbrel Store commit: 018d29a8668e923c7f1a3447fc12273939aefbb8
publication verification: FoxForge run 34440021792
Store post-merge package gate: 34509996521
Store post-merge release gate: 34509996582
target semantic release: v0.1.0-alpha.5 (not published)
```

Candidate 1–5 evidence is historical and must not be relabeled as Candidate 6 evidence. Documentation commits after the frozen application source are not part of the runtime identity.

> [!IMPORTANT]
> Candidate 6 is authorized for physical validation, but physical Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro validation has **not** been completed by CI or publication. Editing the installed package definition after evidence starts invalidates that evidence and requires a new immutable candidate.

## Operator authentication

Umbrel supplies a deterministic per-app `APP_PASSWORD`; the Candidate 6 package maps it to:

```text
FOXFORGE_COMMAND_TOKEN=${APP_PASSWORD}
```

The package exposes the FoxForge app password through the Umbrel UI so normal operators do not need terminal lookup.

To use protected actions:

1. open FoxForge through Umbrel;
2. open **Operator Access / Unlock writes**;
3. enter the FoxForge app password shown by Umbrel;
4. use protected commands in the current tab;
5. reload/close the tab or choose Lock to clear the browser-held credential.

Umbrel App Proxy remains defense in depth and is not a FoxForge application principal. Direct protected writes still require the correct Bearer credential. Tokenless trusted-browser mode remains unsupported.

## Candidate 6 filament-accounting mode

The generic FoxForge runtime default remains:

```text
FOXFORGE_FILAMENT_ACCOUNTING_MODE=disabled
```

The immutable Candidate 6 Umbrel package intentionally sets:

```text
FOXFORGE_FILAMENT_ACCOUNTING_MODE=bambu-validation
```

This provider-scoped validation mode applies the common pre-dispatch reservation/assignment/capacity gate only to printers configured with `adapter_kind == "bambu"`. It does not enable Moonraker/Klipper accounting, does not choose a physical source/toolhead, and does not derive consumed grams from progress/vendor telemetry.

Validation must record `/api/v1/diagnostics/persistence` and confirm:

```json
{
  "mode": "bambu-validation",
  "enforcedAdapterKinds": ["bambu"]
}
```

Do not edit Compose in place to alter accounting mode and then claim the published Candidate 6 identity.

## Packaging model

Candidate 6 uses:

- ordinary Docker bridge networking;
- no host networking;
- no privileged mode or extra Linux capabilities;
- no Docker socket access;
- `${APP_DATA_DIR}/data:/data` persistence;
- `/healthz` container health check;
- the exact digest-pinned multi-architecture FoxForge image above.

The Store package gate passed public anonymous runtime smoke for both `linux/amd64` and `linux/arm64` before and after merge.

## Printer networking and discovery

Bambu and Moonraker communication occurs from the FoxForge container to printer addresses on the LAN. Bambu discovery remains conservative:

- FoxForge may suggest bounded private RFC1918 networks visible from the server/container;
- the operator explicitly selects a suggestion or enters the private CIDR manually;
- scanning is limited to `/22` or smaller networks;
- discovery results remain candidates only;
- authenticated test-before-save remains authoritative;
- manual Bambu entry remains available when discovery cannot see the printer.

## Install Candidate 6

1. Add or refresh `https://github.com/MikeFox303/umbrel-3d-printing-store` as a Community App Store in Umbrel.
2. Select **FoxForge** / `my3d-foxforge`.
3. Confirm package version `0.1.0-alpha.4.3-umbrel.6`.
4. Install/update without manual Compose/container modifications.
5. Confirm the app starts and `/healthz` succeeds.
6. Obtain the FoxForge app password from the Umbrel UI and unlock writes through Operator Access.
7. Follow the exact [Pre-Alpha 5 Bambu physical-validation runbook](../../docs/testing/pre-alpha-5-bambu-physical-validation.md).

Successful package CI or installation alone is not physical X2D acceptance.

## Persistence and upgrades

Persistent `/data` includes application configuration, SQLite state, SecretStore data and staged artifacts. Back up the complete directory before early-alpha upgrades and treat it as sensitive.

A changed application source, image digest or package definition is a new physical-test target. Evidence from an earlier candidate may be retained historically but must not be silently carried forward.

## Remaining gate

Final Alpha 5 remains blocked on physical Candidate 6 Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro acceptance, including GUI operator access, setup negative paths, rollback-safe update, partial X2D status, reconnect recovery, thermal/material topology, immutable 3MF routing, provider-scoped filament accounting with weighed-spool evidence, exactly-one project upload/start and guarded job control.
