<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<!-- Copyright (C) 2026 MikeFox303 -->

# Alpha 4 Fix 1 — interface validation and release plan

Date: 2026-09-05
Status: implementation and validation in progress
Target: first corrective release after `v0.1.0-alpha.4`

## Why this fix exists

Real Alpha 4 use through Umbrel on an iPhone exposed responsive-shell regressions that were not caught by the previous browser matrix. A desktop report confirmed that at least one root cause — the globally fixed operator-access control — is not phone-specific. The first Alpha 4 fix therefore treats this as a cross-viewport interface correction rather than a narrow-phone patch.

Observed or code-confirmed problems:

1. The global operator command-token form is mounted outside the main application shell and was permanently fixed over application content. On a phone it obscures queue, material and inventory controls; on desktop it can also cover lower-right content.
2. The narrow-phone sidebar retained desktop-oriented footer/runtime layout, producing excessive vertical dead space before the workspace.
3. Add Printer was implemented as a detached fixed control, so it could collide with browser chrome or the operator control and did not belong to the normal desktop topbar flow.
4. The previous Playwright desktop viewport was `1440x900`, so it did not explicitly represent a normal 16:9 desktop and there was no ultrawide 32:9 acceptance target.
5. Responsive acceptance covered application behavior, but did not assert horizontal overflow, shell bounds, cross-control overlap, compact phone shell height, or 32:9 content centering.

## Validation matrix

The production-container Playwright acceptance matrix for Fix 1 is:

| Target | Viewport | Additional emulation | Purpose |
| --- | ---: | --- | --- |
| Phone | 390x844 | DPR 3, touch, mobile context | iPhone-class narrow layout |
| Tablet | 900x1024 | normal browser context | preserve existing intermediate breakpoint |
| Desktop 16:9 | 1920x1080 | normal browser context | representative PC desktop |
| Desktop 32:9 | 5120x1440 | normal browser context | super-ultrawide PC |

Every target runs against the built production Docker image, not the Vite development server.

The responsive shell is checked on all public SPA workspaces:

- `/`
- `/printers`
- `/queue`
- `/materials`
- `/inventory`
- `/farm`
- `/system`

## Fix scope

### Operator access

- collapsed, small control by default on phone and desktop;
- expanded token form only on explicit operator action;
- successful unlock returns to a compact unlocked state;
- Lock remains directly reachable after unlock;
- token remains memory-only and existing command authentication semantics are unchanged;
- expanded control stays inside viewport and respects safe-area insets.

### Application shell

- remove excessive narrow-phone sidebar height and hide duplicate footer/runtime presentation on narrow phones;
- keep all seven primary routes reachable;
- keep the narrow topbar compact;
- reserve bottom safe space for mobile browser chrome and the compact operator control.

### Add Printer

- keep Add Printer in normal topbar layout rather than a detached fixed position;
- prevent overlap with operator access at every target viewport;
- preserve one canonical Add Printer entry point.

### Ultrawide behavior

- do not stretch working content across the entire 32:9 panel;
- retain the existing bounded content width and center it inside the main column;
- sidebar remains anchored normally and workspace content remains readable.

## Acceptance criteria

Fix 1 must not be released until all of the following are true:

1. No tested route has horizontal document overflow at phone, tablet, 16:9 or 32:9.
2. Sidebar, topbar, main content, Add Printer and operator access remain within viewport bounds.
3. Collapsed operator access does not overlap Add Printer and is no taller than a compact control.
4. The operator token form is hidden by default on every target viewport and opens only on request.
5. Unlock and Lock remain functional; the command token is not persisted to localStorage, sessionStorage or the URL.
6. On the phone target, sidebar height is below 120 px and topbar height is below 90 px.
7. Phone content is not obscured by the operator control or mobile browser safe area.
8. On 32:9, `.content` stays bounded to the product max width and is horizontally centered within `.main-column`.
9. Queue staging/enqueue, inventory create/correct/history/archive, spool assignment/unassignment and Add Printer dialog flows remain usable.
10. EN, RU and UK translations do not create obvious clipping or horizontal overflow in the shell and operator-access control.
11. Existing frontend unit/build tests, backend tests, security gates, deployment-auth contract, production container smoke and browser acceptance are green.
12. A real-device smoke check on the reported iPhone/Umbrel path confirms the blocking overlay and excessive vertical gap are gone before publishing the Umbrel update.

## Automated evidence

`frontend/e2e/responsive-layout.spec.ts` provides explicit regression assertions for:

- shell visibility and bounds;
- absence of document-level horizontal overflow;
- Add Printer/operator-access collision;
- compact phone sidebar/topbar;
- compact operator state;
- centered bounded 32:9 content.

The Playwright matrix also continues the functional browser tests. Screenshots for Overview, Queue and Inventory are captured for phone, 16:9 and 32:9 runs as diagnostic evidence.

## Release identity

The preferred public identity for “Alpha 4 — Fix 1” is:

- product/GitHub tag: `v0.1.0-alpha.4.1`;
- frontend/Umbrel/GHCR version: `0.1.0-alpha.4.1`;
- Python PEP 440 version: `0.1.0a4.post1`.

This keeps the fix clearly attached to Alpha 4 instead of presenting it as the next feature alpha. Before tagging, the release identity validator and its tests must be extended to accept this optional Alpha-fix form while continuing to reject inconsistent package/image/tag identities.

## Release sequence

1. Finish PR #97 and make the full phone/tablet/16:9/32:9 browser matrix green.
2. Review Playwright failure traces/screenshots and perform the real iPhone/Umbrel smoke check.
3. Merge the responsive fix to `main` only after all required CI is green.
4. Prepare a dedicated release commit/PR that updates backend/frontend/release identity to `0.1.0-alpha.4.1`, updates the validator/tests, and adds Fix 1 release notes.
5. Run the complete release gate from the exact release candidate commit.
6. Tag `v0.1.0-alpha.4.1`. The release workflow must build and verify both `linux/amd64` and `linux/arm64` and publish the immutable GHCR image.
7. Record the verified multi-architecture image digest and GitHub release evidence.
8. In `MikeFox303/umbrel-3d-printing-store`, update the FoxForge package version/source version/source commit/source archive/release notes and pin `docker-compose.yml` to that verified image digest. Never switch Umbrel to a floating tag.
9. Run Store/Compose/package validation and an Umbrel upgrade smoke that preserves `/data`, inventory, queue and artifact state and confirms the existing auth-mode contract.
10. Merge the Umbrel Store update only after those checks pass. This makes Fix 1 available through normal Umbrel application update flow.

## Rollback

The current Alpha 4 Umbrel package is the rollback point. If Fix 1 fails post-publication validation, restore the previous FoxForge Umbrel package metadata and its known immutable Alpha 4 image digest rather than rebuilding an old tag. Persistent `/data` must not be deleted during rollback.

## Out of scope

This corrective release must not opportunistically resume frozen P3 automatic filament accounting or introduce unrelated printer-domain behavior. The goal is a narrowly reviewable UI/release correction with no reduction in Bambu depth, no change to vendor abstractions and no deployment-contract weakening.
