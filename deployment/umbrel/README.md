# Umbrel deployment

This directory is reserved for FoxForge's Umbrel application packaging.

The prerequisite unified FoxForge runtime now exists: backend, compiled frontend, `/api/v1`, SQLite persistence and Docker startup smoke testing are integrated. Umbrel packaging is therefore a **next release gate**, not a blocker waiting on a future server entrypoint.

Umbrel must package the same FoxForge container/runtime used by normal Docker deployments rather than maintain a divergent application fork.

## Target constraints

- ARM64-friendly defaults for Raspberry Pi 5 class hosts;
- persistent application data through Umbrel volumes;
- App Proxy integration and health checks;
- no privileged Docker socket access unless a future documented feature genuinely requires it;
- no separate Umbrel-only backend/frontend behavior;
- release/version metadata tied to tested immutable FoxForge images;
- printer connectivity through the same explicit runtime configuration and adapter contracts used by normal Docker deployments.

## Required before calling the Umbrel package ready

1. validate the unified FoxForge image on representative ARM64 hardware;
2. define release image/tag/digest policy;
3. document persisted-state upgrade/migration behavior;
4. create Umbrel manifest, icon/gallery metadata and App Proxy configuration;
5. verify first-start `/data` permissions and persistence under Umbrel mounts;
6. run end-to-end health/UI/API smoke tests on Umbrel;
7. confirm configured Bambu/Moonraker printers remain reachable from the Umbrel networking model;
8. keep all platform-specific packaging changes outside core application/domain behavior.

The Umbrel package must not imply production printer support until physical Bambu LAN/X2D and Moonraker/OpenKE validation has also passed.
