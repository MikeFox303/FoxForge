# Umbrel deployment

FoxForge `v0.1.0-alpha.3` is available as `my3d-foxforge` in the companion Community App Store:

- Store repository: `MikeFox303/umbrel-3d-printing-store`
- Store app ID: `my3d-foxforge`
- Umbrel app port: `8283`
- FoxForge server port inside the app network: `8000`
- release image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.3`
- immutable multi-architecture digest: `sha256:efab08cdbfa515d83b665a71c2b48642d530c4880ec0d7b85b5488a34e2acc94`

The package reuses the exact FoxForge release image rather than maintaining an Umbrel-specific application fork.

## Important authentication status

The published `v0.1.0-alpha.3` Store Compose does **not** configure `FOXFORGE_COMMAND_TOKEN` and does not provide an ADR-0005-compatible authenticated browser bootstrap. Therefore FoxForge does **not** claim this historical Umbrel package as a validated write-capable deployment.

Umbrel App Proxy remains useful authenticated defense in depth, but it is not by itself a FoxForge application principal. Current-source FoxForge deliberately rejects `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true`; forwarding headers or a private Docker network are not sufficient proof to mint an operator credential.

The `alpha.3` package may still be used for controlled installation/read-path testing, but documentation must not promise that **Add Printer**, Queue mutation, inventory mutation or printer-control workflows work end to end through that package. A future Umbrel package must either:

1. configure and test an application authentication bootstrap compatible with [ADR 0005](../../docs/adr/0005-browser-command-authentication.md); or
2. deliberately present protected writes as unavailable/read-only with a truthful explanation.

See the [deployment authentication acceptance contract](../../docs/testing/deployment-auth-contract.md).

## Packaging model

The Umbrel package keeps the deployment small and conservative:

- Umbrel App Proxy fronts the FoxForge server and is defense in depth rather than the sole write-security boundary;
- normal Docker bridge networking is used;
- no `network_mode: host` is required for the current explicit-IP Bambu LAN and Moonraker transports;
- no privileged mode, extra Linux capabilities or Docker socket access is granted;
- `${APP_DATA_DIR}/data` is mounted as `/data`;
- `/healthz` is used for the container health check;
- first start creates persistent application state under `/data`.

Printer discovery, Bambu Virtual Printer and features that may require different LAN/network behavior remain deferred until their contracts and physical validation are complete.

## Existing package validation evidence

The companion Store package has validation for:

- the Umbrel manifest and Compose contract;
- Compose rendering with an App Proxy overlay;
- anonymous pull of the immutable GHCR image;
- startup, `/healthz` and SPA response on Linux `amd64`;
- startup, `/healthz` and SPA response on Linux `arm64` under CI/QEMU;
- creation and persistence of the application data directory.

This proves that the historical package is pullable and executable on the published architectures. It does **not** prove browser write authentication, Raspberry Pi 5 behavior or printer-network reachability.

## Installing for controlled alpha testing

1. Add `https://github.com/MikeFox303/umbrel-3d-printing-store` as a Community App Store in UmbrelOS if needed.
2. Install **FoxForge**.
3. Open FoxForge and verify that the UI and read endpoints load.
4. Treat protected write workflows in the published `alpha.3` package as **not validated/supported** until a later package provides the required FoxForge application authentication contract.

Do not use the historical package as evidence that Add Printer, queue submission, inventory mutations or printer controls are production-ready on Umbrel.

## Current alpha networking

Bambu LAN configuration uses an explicit printer host plus LAN access code and serial number. Moonraker uses an explicit `base_url` and optional API key. Current source has security and persistence improvements beyond `alpha.3`; those changes are not delivered to the historical package until a new guarded release and Store update occur.

Bridge networking remains the supported deployment direction for explicit-IP transports. Discovery, Virtual Printer and future transports that need broader LAN access require separate design and physical validation.

## Persistence and upgrades

Persistent `/data` contains runtime configuration, SQLite state and staged artifacts. Current source now includes explicit migration/version ownership, but the published `alpha.3` remains an older immutable build.

Back up FoxForge application data before upgrading between early alpha releases. `/data` backups must be treated as sensitive because credential-related recovery material may exist in later source versions.

## Required evidence before the next write-capable Umbrel package

Before FoxForge can claim a write-capable Umbrel deployment, record all of the following against the exact future package:

1. the package supplies an ADR-0005-compatible FoxForge application credential/bootstrap or intentionally remains read-only;
2. Raspberry Pi 5 install, restart and persistence are validated on physical ARM64 hardware;
3. Add Printer succeeds through the actual Umbrel browser/proxy path when writes are enabled;
4. at least one additional protected command succeeds through the same path and invalid/missing credentials fail closed;
5. tokenless `/api/v1/operator-session` does not issue credentials;
6. Bambu Lab X2D and Moonraker/OpenKE are reachable from the actual Umbrel network environment;
7. real upload/start/lifecycle/control/completion behavior is validated on both printer families;
8. upgrade/migration behavior is tested between the relevant published package versions.

Until that evidence exists, AUD-003/AUD-004 remain deployment-validation findings rather than resolved production claims.

## Versioning note

The current Umbrel package is pinned to the immutable `v0.1.0-alpha.3` multi-architecture digest. Changes merged to FoxForge `main` are not delivered through a floating release tag; they require a new guarded FoxForge release and a corresponding Store package update.
