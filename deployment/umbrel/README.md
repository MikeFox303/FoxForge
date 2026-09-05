# Umbrel deployment

FoxForge `v0.1.0-alpha.4.2` is packaged as `my3d-foxforge` in the companion Community App Store:

- Store repository: `MikeFox303/umbrel-3d-printing-store`
- Store app ID: `my3d-foxforge`
- package version: `0.1.0-alpha.4.2`
- Store package commit: `e842c411e26689609e9bbba4681df903f3624bbd`
- Umbrel app port: `8283`
- FoxForge server port inside the app network: `8000`
- release commit: `fe5b3437f1e342548df74ded78557c771ef40710`
- release image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2`
- immutable multi-architecture digest: `sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6`

The package reuses the exact guarded FoxForge release image rather than maintaining an Umbrel-specific application fork.

## Authentication model

The Alpha 4.2 package is configured as **write-enabled** while preserving the FoxForge ADR 0005 trust model.

Umbrel provides a unique per-app `APP_PASSWORD`. The package passes it to FoxForge as:

```text
FOXFORGE_COMMAND_TOKEN=${APP_PASSWORD}
```

To use protected actions:

1. open FoxForge through Umbrel App Proxy;
2. choose **Unlock writes** in FoxForge;
3. enter the FoxForge app password shown by Umbrel;
4. FoxForge keeps the credential only in JavaScript memory for the current tab;
5. protected commands send it as `Authorization: Bearer ...`;
6. reload/tab close, explicit Lock or HTTP 401 clears the browser copy.

Umbrel App Proxy remains defense in depth but is **not** itself a FoxForge application principal. Forwarding headers or a private Docker network do not mint a FoxForge credential.

Current production invariants remain unchanged:

- direct protected writes without the correct Bearer fail closed;
- tokenless `/api/v1/operator-session` does not issue a credential;
- `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is rejected by the production runtime;
- a future tokenless proxy bootstrap would require a new/amended ADR and cryptographically authenticated assertion contract.

See [ADR 0005](../../docs/adr/0005-browser-command-authentication.md) and the [deployment authentication acceptance contract](../../docs/testing/deployment-auth-contract.md).

## Packaging model

The Umbrel package keeps the deployment small and conservative:

- Umbrel App Proxy fronts the FoxForge server;
- normal Docker bridge networking is used;
- no `network_mode: host` is required for the current explicit-IP Bambu LAN and Moonraker transports;
- no privileged mode, extra Linux capabilities or Docker socket access is granted;
- `${APP_DATA_DIR}/data` is mounted as `/data`;
- `/healthz` is used for the container health check;
- first start creates current schema state under `/data`;
- the exact immutable Alpha 4.2 multi-architecture digest is pinned.

Printer discovery, Bambu Virtual Printer and features that may require different LAN/network behavior remain deferred until their contracts and physical validation are complete.

## Package CI evidence

The companion Store package gate validates:

- package version and exact immutable release digest;
- the `APP_PASSWORD` → `FOXFORGE_COMMAND_TOKEN` application credential mapping;
- Umbrel Compose rendering with a representative App Proxy overlay;
- no host networking, privileged mode or Docker socket access;
- anonymous pull of the immutable GHCR image;
- startup, `/healthz` and SPA response on Linux `amd64`;
- startup, `/healthz` and SPA response on Linux `arm64` under CI/QEMU;
- first-start `config.json` schema **2** with an empty printer set;
- creation of `foxforge.sqlite3` and expected mounted-data ownership.

Store PR #28 passed its final Upstream version audit, FoxForge package gate and Store Release Gate before merge. Post-merge `main` also passed FoxForge Umbrel Package run `33980306219` and Store Release Gate run `33980306217`.

This proves the package definition and release image are consistent and runnable on the published architectures. It does **not** prove Raspberry Pi 5 hardware behavior, the real Umbrel proxy/write path, physical printer-network reachability or production readiness.

## Installing for controlled alpha testing

1. Add `https://github.com/MikeFox303/umbrel-3d-printing-store` as a Community App Store in UmbrelOS if needed.
2. Install or update **FoxForge** to `0.1.0-alpha.4.2`.
3. Verify the package resolves to `ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6` before collecting canonical physical evidence.
4. Open FoxForge and verify the UI/read paths load.
5. For protected commands, choose **Unlock writes** and enter the app password shown by Umbrel.
6. Add a printer through the UI only when you are prepared to validate actual network reachability and printer behavior.
7. Keep a complete backup of FoxForge `/data` before early-alpha upgrades.

Do not treat a successful install or CI smoke as evidence that X2D/OpenKE print/control workflows are production-ready.

## Current alpha networking

Bambu LAN configuration uses an explicit printer host plus LAN access code and serial number. Moonraker uses an explicit `base_url` and optional API key.

Bridge networking remains the supported deployment direction for explicit-IP transports. The real Umbrel host/container network must still be validated against representative printers. Discovery, Virtual Printer and future transports that need broader LAN access require separate design and physical validation.

## Persistence and upgrades

Persistent `/data` includes:

- `config.json` — current schema version **2**;
- `foxforge.sqlite3` — SQLite schema owner via `PRAGMA user_version`, current version **1**;
- SecretStore data including printer credentials;
- staged artifacts and related runtime state.

Current source includes explicit migration/version ownership, backups and schema validation. Back up the complete `/data` directory before upgrading between early alpha releases and treat those backups as sensitive credential-bearing data.

## AUD-003 remains validation-required

Publishing a correctly configured package does not by itself close AUD-003. Before that finding can become `RESOLVED`, representative evidence must be recorded against the actual Alpha 4.2 package/deployment for:

1. physical Raspberry Pi 5/UmbrelOS install, restart and persistence;
2. the real Umbrel browser/App Proxy path with successful authenticated protected writes;
3. missing/wrong application credentials failing closed;
4. direct-backend protected writes failing without the correct Bearer;
5. tokenless `/api/v1/operator-session` remaining disabled;
6. Bambu Lab X2D and Moonraker/OpenKE reachability from the actual Umbrel network environment;
7. real upload/start/lifecycle/control/completion behavior on both printer families;
8. representative SSE reconnect/resync behavior through the deployed proxy path;
9. upgrade/migration behavior between relevant published package versions;
10. the redacted evidence manifest passing `python -m foxforge.testing.physical_evidence <manifest> --require aud003`.

AUD-004 remains resolved for the explicit-token trust model. AUD-013 separately remains validation-required for real X2D certificate observations.

Use the [physical validation runbook](../../docs/testing/physical-validation-runbook.md) for the exact Alpha 4.2 identity and evidence procedure.

## Versioning note

The current Umbrel package is pinned to the immutable `v0.1.0-alpha.4.2` multi-architecture OCI digest. Changes merged to FoxForge `main` are not delivered through a floating semantic release tag; they require a new guarded FoxForge release and a corresponding Store package update.
