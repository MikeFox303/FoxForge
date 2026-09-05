# Alpha 4 Fix 2 release-readiness gate — 2026-09-05

**Target:** `v0.1.0-alpha.4.2`  
**Scope:** stabilization only; no P3 feature work  
**Primary fix:** PR #99, Add Printer modal isolation and responsive UI regression coverage

## Release rule

Do not publish `v0.1.0-alpha.4.2` merely because the modal fix compiles. The exact release commit must be treated as the test subject and must pass the complete automated release gate before Git tag/image publication.

Required automated gates:

- backend Ruff lint and format checks;
- full backend tests on Python 3.12 and 3.13, with the configured branch-coverage threshold on 3.12;
- frontend TypeScript check, unit tests and production build;
- production-container browser acceptance on phone 390x844, tablet 900x1024, desktop 1920x1080 and 5120x1440;
- every primary route bounded without horizontal viewport overflow;
- Russian and Ukrainian route-layout checks on phone and 16:9 desktop;
- Add Printer modal opened and verified for viewport ownership, opaque surface, z-order, scrolling and closing behavior;
- retained browser screenshots for manual visual review;
- deployment authentication contract;
- container health/persistence smoke;
- npm and Python dependency audits plus HIGH/CRITICAL final-image scan;
- no public production source maps;
- immutable release-identity validation.

The guarded release workflow itself must rerun the production-container Playwright suite against the exact release commit **before** creating the Git tag or publishing the versioned image. A separate earlier PR run is useful evidence but is not sufficient by itself.

## UI acceptance criteria

For all supported viewport projects:

1. Sidebar/navigation, topbar, route content, Add Printer launcher and operator-access control stay within the viewport.
2. No global horizontal scrolling is introduced on Overview, Printers, Queue, Materials, Inventory, Farm or System.
3. Phone navigation remains compact rather than consuming unused viewport height.
4. 32:9 content remains centered and bounded instead of stretching to the full display width.
5. Add Printer opens exactly one modal rendered under `document.body`, outside sticky/filter stacking contexts.
6. The modal backdrop owns the viewport and the modal is visually opaque; underlying application text must not visually merge with dialog content.
7. Operator access and other global controls cannot render above the modal.
8. Phone modal geometry uses the dynamic viewport and remains usable with iOS safe areas; only modal content scrolls while it is open.
9. Closing restores normal page scrolling.
10. RU/UK text must not create overflow or clipping in the tested phone and desktop layouts.
11. Locked-write and fallback errors in Printer Setup are localized instead of leaking English-only command-client messages into RU/UK dialogs.
12. Operator-access controls use only defined FoxForge theme tokens; no invalid border token may silently drop a border.

## Code-quality acceptance criteria

- No known failing or cancelled required CI checks on the exact PR/release head.
- No release-path bypass that can publish the semantic image before browser acceptance.
- No known unresolved UI defect reproducible in the automated viewport matrix.
- Security/dependency scans remain green.
- Request-local aiohttp state uses typed `RequestKey` storage rather than application keys, keeping the backend test suite free of the `NotAppKeyWarning` that was found during this release-readiness pass.
- P3 draft PR #58 stays frozen and is not mixed into this hotfix.
- No claim of physical-printer validation is made from mocks, fake adapters, browser emulation or container tests.

## Physical-printer handoff

After `v0.1.0-alpha.4.2` is published and the matching Umbrel package pins its immutable digest, that exact package becomes the physical-test target. Follow `docs/testing/physical-validation-runbook.md` and collect secret-safe evidence for:

- Raspberry Pi 5/Umbrel install or update, restart, persistence, App Proxy write path, direct-backend fail-closed behavior, printer reachability and SSE reconnect/resync;
- Bambu Lab X2D connect/reconnect, normalized state, project storage/upload, start acknowledgement, pause/resume/cancel, completion and ambiguous outcomes;
- Moonraker/OpenKE connect/reconnect, upload/checksum/start, pause/resume/cancel, completion/failure and ambiguous outcomes;
- X2D MQTT/FTPS certificate stability and fail-closed pinning behavior;
- browser Add Printer plus another protected command, including memory-only credential behavior after reload.

AUD-003 and AUD-013 remain `VALIDATION REQUIRED` until that real-device evidence is collected and verified. This is expected: the purpose of alpha.4.2 is to remove software/UI blockers so physical validation can finally begin, not to pretend CI has already performed it.
