# Alpha 4 Fix 2 release evidence — 2026-09-05

**Release:** `v0.1.0-alpha.4.2`  
**Release commit:** `fe5b3437f1e342548df74ded78557c771ef40710`  
**State:** released and published in the Umbrel 3D Printing Store; physical validation is still pending.

This record is intentionally committed after the immutable release tag. It documents the release and Store publication chain without moving or rewriting the released commit.

## Release identity

- GitHub release workflow: run `33973431720`, completed successfully on exact commit `fe5b3437f1e342548df74ded78557c771ef40710`.
- Annotated tag: `v0.1.0-alpha.4.2`.
- Tag object: `9858eb5b44e6d8affb34db3def9e6d8e2a3d7b88`.
- The annotated tag resolves to exact commit `fe5b3437f1e342548df74ded78557c771ef40710`.
- GitHub release `FoxForge v0.1.0-alpha.4.2` is published as a pre-release.
- All eight ordinary `push` workflow runs associated with the exact release commit completed successfully.

The release workflow is fail-closed: it performs immutable identity preflight, backend and frontend validation, builds and smoke-tests the production image, runs exact-commit browser acceptance, verifies no public source maps, and revalidates release identity before creating the Git tag. Only after the tag is created does it publish the versioned `linux/amd64` + `linux/arm64` image and create the GitHub pre-release.

## Exact-commit browser acceptance

The release workflow reran Browser Acceptance against the production smoke container built from the exact release commit before tag or image publication.

Release evidence artifact:

- artifact id: `9971632222`;
- artifact name: `foxforge-release-browser-evidence-fe5b3437f1e342548df74ded78557c771ef40710`;
- GitHub Actions artifact ZIP digest: `sha256:6c769159c63dd71fb61a8099353736c360735e6b4656078a3489c354b6667bb6`;
- retained screenshots: 66 PNG files.

The screenshots were manually reviewed during the release pass for the primary route matrix, phone/tablet/16:9/32:9 geometry, RU/UK layouts, Add Printer modal behavior and Operator Access states. This is browser/container evidence only; it is not physical-printer evidence.

The artifact ZIP digest above is **not** the GHCR image digest and must never be used as an Umbrel image pin.

## Published container identity

Canonical release image:

`ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2`

Verified OCI index digest:

`sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6`

Published platforms:

- `linux/amd64`;
- `linux/arm64`.

The multi-architecture build metadata is bound to release revision `fe5b3437f1e342548df74ded78557c771ef40710`. Deployment packaging must therefore use the semantic version plus the immutable OCI digest together:

`ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6`

## Umbrel Store publication

Store repository: `MikeFox303/umbrel-3d-printing-store`.

Publication PR: `#28` — `release(foxforge): publish v0.1.0-alpha.4.2`.

Final PR head:

`8647e17888f104944b6ea8066887385ea3235a96`

PR-head validation completed successfully:

- Upstream version audit run `33980174535`;
- FoxForge Umbrel Package run `33980174536`;
- Store Release Gate run `33980174542`.

The first package-contract attempt correctly failed because the Store regression test still expected the previous Alpha 4.1 image identity. The fix advanced that test to the exact Alpha 4.2 semantic version and immutable digest without weakening the invariant. The final package contract, Compose validation, command-token bootstrap and public runtime smoke tests passed.

PR #28 was squash-merged only after the final four-file diff and exact head were re-verified. Store `main` became:

`e842c411e26689609e9bbba4681df903f3624bbd`

The merged package preserves the required deployment contract:

- image: `ghcr.io/mikefox303/foxforge:0.1.0-alpha.4.2@sha256:39d2f2fd02ed8dafe68ce741543642a62d9f3669d2deeb118bc5abce61589fc6`;
- persistent volume: `${APP_DATA_DIR}/data:/data`;
- write credential bootstrap: `FOXFORGE_COMMAND_TOKEN: "${APP_PASSWORD}"`;
- Umbrel app version: `0.1.0-alpha.4.2`.

Post-merge validation on Store `main` also completed successfully:

- FoxForge Umbrel Package run `33980306219` — success;
- Store Release Gate run `33980306217` — success.

## Validation boundary and next target

No CI run, QEMU runtime smoke-test, browser emulator, mock adapter or container test in this record constitutes validation on the user's actual hardware.

The exact physical-test target is now fixed: install/update the Umbrel package from Store commit `e842c411e26689609e9bbba4681df903f3624bbd`, which pins the Alpha 4.2 image digest above, and follow `docs/testing/physical-validation-runbook.md`.

Required real-device coverage remains:

- Raspberry Pi 5 / Umbrel install-update, restart, persistence, App Proxy write flow and SSE reconnect/resync;
- Bambu Lab X2D + AMS 2 Pro connect/reconnect, storage/upload, start acknowledgement, pause/resume/cancel and terminal/ambiguous outcomes;
- Ender 3 V3 KE with OpenKE/Moonraker connect/reconnect, upload/checksum/start, pause/resume/cancel and terminal/ambiguous outcomes;
- X2D MQTT/FTPS certificate stability and fail-closed pinning behavior;
- browser Add Printer and another protected command with memory-only operator credential behavior.

`AUD-003` and `AUD-013` remain **`VALIDATION REQUIRED`** until secret-safe real-device evidence is collected and reviewed.

## Release evidence acceptance criteria

- [x] Release tag resolves to the exact tested release commit.
- [x] Exact-commit Browser Acceptance ran before tag/image publication.
- [x] Browser artifact identity is recorded separately from the OCI image identity.
- [x] Multi-architecture GHCR OCI digest and platforms are recorded.
- [x] Umbrel package is pinned by semantic version plus immutable digest.
- [x] Persistent data and command-token contracts are preserved.
- [x] PR-head and post-merge Store gates are green.
- [x] No physical validation claim is made from automated evidence.
- [ ] Physical validation runbook completed on Raspberry Pi 5, X2D + AMS 2 Pro, and Ender 3 V3 KE/OpenKE.
- [ ] `AUD-003` and `AUD-013` closed with reviewed real-device evidence.
