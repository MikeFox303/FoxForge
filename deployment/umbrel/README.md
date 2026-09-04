# Umbrel deployment

FoxForge `v0.1.0-alpha.3` is available as `my3d-foxforge` in the companion Community App Store:

- Store repository: `MikeFox303/umbrel-3d-printing-store`
- Store app ID: `my3d-foxforge`
- Umbrel app port: `8283`
- FoxForge server port inside the app network: `8000`
- Release image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.3`
- Immutable multi-architecture digest: `sha256:efab08cdbfa515d83b665a71c2b48642d530c4880ec0d7b85b5488a34e2acc94`

The current Community App package was updated through Store PR #24 and reuses the exact FoxForge release image rather than maintaining an Umbrel-specific application fork.

## Packaging model

The Umbrel package deliberately keeps the deployment small and conservative:

- Umbrel App Proxy fronts the FoxForge server and remains an authenticated defense-in-depth boundary;
- FoxForge `alpha.3` also enforces its own application-level command authentication/authorization for remote mutations, so App Proxy is not the sole write-security boundary;
- normal Docker bridge networking is used;
- no `network_mode: host` is required for the current explicit-IP Bambu LAN and Moonraker transports;
- no privileged mode, extra Linux capabilities or Docker socket access is granted;
- `${APP_DATA_DIR}/data` is mounted as `/data` using short/string bind syntax compatible with the current Store package contract;
- `/healthz` is used for the container health check;
- first start creates `/data/config.json` and `/data/foxforge.sqlite3`;
- staged `.gcode`/`.3mf` artifacts are stored under persistent `/data/artifacts` by the released queue workflow.

Printer discovery, Bambu Virtual Printer and other features that may require different LAN/network behavior are intentionally deferred until their contracts and physical validation are complete.

## Validation evidence

The Store package has dedicated validation that covers:

- the Umbrel manifest and Compose contract;
- rendering through `docker compose config` with an App Proxy overlay;
- anonymous pull of the exact immutable GHCR release image without registry credentials;
- startup, `/healthz` and SPA response on Linux `amd64`;
- startup, `/healthz` and SPA response on Linux `arm64` under CI/QEMU;
- creation and persistence of the FoxForge application data directory;
- anonymous runtime smoke of the published alpha.3 image on both supported architectures.

The `v0.1.0-alpha.3` guarded release independently passed backend installation, Ruff lint/format, **171 backend tests**, frontend typecheck, **28 frontend tests**, Vite production build and unified release-image smoke before multi-architecture publication. The companion Store package was then pinned to the resulting immutable digest and validated again on Store `main`.

This proves the released image is publicly pullable and executable for both published architectures. It does **not** replace representative Raspberry Pi 5 testing or real printer-network validation.

## Installing from UmbrelOS

1. Add `https://github.com/MikeFox303/umbrel-3d-printing-store` as a Community App Store in UmbrelOS if it is not already registered.
2. Refresh/wait for the Community Store catalog update.
3. Install **FoxForge** from the Umbrel App Store UI.
4. Open FoxForge once so the persistent `/data` state is initialized.
5. Use **Add Printer** in the FoxForge web UI to configure a Bambu LAN or Moonraker/Klipper printer. Alpha.3 supports authenticated add/update/remove/test/reconnect flows; direct `config.json` editing is no longer the normal setup path.
6. Use the Queue UI to select a local `.gcode` or `.3mf`, hash and stage its bytes, enqueue the job and explicitly start it. `INDETERMINATE` starts require explicit reconciliation and are never blindly retried.

The Store package also contains Bambu LAN and Moonraker/Klipper configuration guidance in `my3d-foxforge/README.md`.

## Current alpha networking

Bambu LAN configuration uses an explicit printer host plus LAN access code and serial number. Moonraker uses an explicit `base_url` and optional API key. These transports use the same adapter factories and runtime configuration as normal Docker deployments.

A printer being powered off or unreachable does not prevent FoxForge itself from starting. The runtime leaves the printer offline and retries in the background.

Bridge networking remains the supported deployment model for the current explicit-IP transports. Discovery, Virtual Printer and any future transport that requires different LAN behavior must receive separate design and physical validation before changing this contract.

## Persistence and upgrades

Persistent `/data` currently includes:

- `config.json`;
- `foxforge.sqlite3`;
- staged print artifacts under `/data/artifacts`.

Persistence compatibility is still pre-stable. Back up the FoxForge application data directory before upgrading between early alpha releases.

The Umbrel package is pinned to an immutable release digest. A change merged to FoxForge `main` is not delivered to existing installations through a floating tag; it requires a guarded FoxForge release and a corresponding Store package update.

## Remaining deployment validation

Before FoxForge should be described as production-ready on Umbrel, the following evidence is still required:

1. representative Raspberry Pi 5 / physical ARM64 installation, restart and persistence validation;
2. configured Bambu Lab X2D LAN connectivity from the actual Umbrel network environment;
3. configured Moonraker/OpenKE connectivity from the actual Umbrel network environment;
4. real upload/start/lifecycle/completion and ambiguous-start reconciliation tests on both printer families;
5. persisted-state upgrade/migration testing across later FoxForge releases;
6. future network design validation before enabling discovery or Virtual Printer.

The Community App package therefore makes FoxForge alpha.3 **installable for controlled testing**, but it does not imply production-validated printer support.

## Versioning note

The current Umbrel package is pinned to the released `v0.1.0-alpha.3` multi-architecture digest. Future FoxForge source changes require a new tested release and a corresponding immutable Store package update.
