# Umbrel deployment

FoxForge `v0.1.0-alpha.1` is available as `my3d-foxforge` in the companion Community App Store:

- Store repository: `MikeFox303/umbrel-3d-printing-store`
- Store app ID: `my3d-foxforge`
- Umbrel app port: `8283`
- FoxForge server port inside the app network: `8000`
- Release image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.1`
- Immutable multi-architecture digest: `sha256:f9bdb39893162df49e3a6eddfcdc10c3f950fbccaa4e3abb631711bd0605e54b`

The Community App package was merged through Store PR #20 and reuses the exact FoxForge release image rather than maintaining an Umbrel-specific application fork.

## Packaging model

The first Umbrel package deliberately keeps the deployment small and conservative:

- Umbrel App Proxy fronts the FoxForge server;
- standard Umbrel App Proxy authentication remains enabled because the alpha does not yet provide its own user login;
- normal Docker bridge networking is used;
- no `network_mode: host` is required for the current explicit-IP Bambu LAN and Moonraker transports;
- no privileged mode, extra Linux capabilities or Docker socket access is granted;
- `${APP_DATA_DIR}/data` is mounted as `/data` using short/string bind syntax compatible with umbrelOS 1.7.4;
- `/healthz` is used for the container health check;
- first start creates `/data/config.json` and `/data/foxforge.sqlite3`.

Printer discovery, Bambu Virtual Printer and other features that may require different LAN/network behavior are intentionally deferred until their contracts and physical validation are complete.

## Validation evidence

The package has a dedicated Store workflow that validates:

- the Umbrel manifest and Compose contract;
- rendering through `docker compose config` with an App Proxy overlay;
- anonymous pull of the exact immutable GHCR release image without registry credentials;
- startup, `/healthz` and SPA response on Linux `amd64`;
- startup, `/healthz` and SPA response on Linux `arm64` under CI/QEMU;
- creation of `config.json` and `foxforge.sqlite3` on a fresh persistent mount;
- application data ownership as UID/GID `1000:1000`;
- `config.json` ownership/mode `1000:1000 0600` and the expected initial schema.

The existing Store Release Gate also passed after the FoxForge package was added, including its regression tests for the other 3D-printing applications.

This proves the released image is publicly pullable and executable for both published architectures. It does **not** replace representative Raspberry Pi 5 testing or real printer-network validation.

## Installing from UmbrelOS

1. Add `https://github.com/MikeFox303/umbrel-3d-printing-store` as a Community App Store in UmbrelOS if it is not already registered.
2. Refresh/wait for the Community Store catalog update.
3. Install **FoxForge** from the Umbrel App Store UI.
4. Open FoxForge once so the empty `/data/config.json` and SQLite database are created.
5. Configure printers in the app data `data/config.json` and restart FoxForge. The alpha web UI does not yet provide printer-configuration writes.

The Store package contains detailed Bambu LAN and Moonraker/Klipper configuration examples in `my3d-foxforge/README.md`.

## Current alpha networking

Bambu LAN configuration uses an explicit printer host plus LAN access code and serial number. Moonraker uses an explicit `base_url` and optional API key. These transports use the same adapter factories and runtime configuration as normal Docker deployments.

A printer being powered off or unreachable does not prevent FoxForge itself from starting. The runtime leaves the printer offline and retries in the background.

## Remaining deployment validation

Before FoxForge should be described as production-ready on Umbrel, the following evidence is still required:

1. representative Raspberry Pi 5 / physical ARM64 installation and restart validation;
2. configured Bambu Lab X2D LAN connectivity from the actual Umbrel network environment;
3. configured Moonraker/OpenKE connectivity from the actual Umbrel network environment;
4. real upload/start/lifecycle/completion tests on both printer families;
5. persisted-state upgrade/migration testing across later FoxForge releases;
6. future network design validation before enabling discovery or Virtual Printer.

The Community App package therefore makes the first alpha **installable for testing**, but it does not imply production-validated printer support.

## Versioning note

The Umbrel package is pinned to the released `v0.1.0-alpha.1` image. Changes merged to FoxForge `main` after that release are intentionally **not** pulled into existing installations through a floating tag. They require a new tested FoxForge release and a corresponding immutable Store package update.
