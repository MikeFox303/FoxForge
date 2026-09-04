# UmbrelOS mobile validation — 2026-09-04

Status: representative real-install validation evidence for `v0.1.0-alpha.2`.

## Evidence received

A real FoxForge installation running under UmbrelOS was opened from a phone and visually reviewed across Overview, Printers, Queue, Materials, Inventory, Farm and System workspaces.

The screenshots are intentionally not committed to the repository because they include local-network/browser details. This note records only the validated product behavior.

## Confirmed

- FoxForge installs and starts under a real UmbrelOS environment.
- The compiled SPA is reachable from a phone browser through the Umbrel application entry point.
- The live FoxForge API is reachable from that SPA; the UI reports the live API runtime rather than demo mode.
- Russian localization renders across the reviewed workspaces.
- The first-run/no-printer state is represented consistently: zero configured printers, empty queue and no reported material systems.
- Navigation between Overview, Printers, Queue, Materials, Inventory, Farm and System works in the installed application.
- The Inventory and System workspaces render from the packaged production build rather than a standalone development server.

## UX finding

Portrait phone layout is functional but too dense and desktop-like. The existing `<=900px` breakpoint successfully collapses the desktop sidebar into a horizontal header and looks substantially better in landscape, but the `<=620px` presentation still wastes vertical space and gives low-value disabled actions too much prominence.

The first mobile refinement therefore targets only narrow phones:

- compact seven-destination navigation using the existing accessible labels;
- preserve a visible live-API status while hiding the unavailable Add Printer action;
- reduce narrow-screen padding and empty-state height;
- use a 2x2 KPI grid on normal phone widths, falling back to one column below 360 px;
- improve definition/diagnostics wrapping and touch target sizing;
- leave tablet/landscape and desktop behavior unchanged.

## Not validated by this evidence

These screenshots do **not** prove:

- Bambu X2D connectivity or print execution;
- Moonraker/OpenKE connectivity or print execution;
- printer reachability from the Umbrel network namespace;
- restart/upgrade persistence;
- automatic filament accounting;
- authenticated mutation APIs;
- a specific CPU architecture or Raspberry Pi model.

Those remain separate validation gates and must not be inferred from successful mobile UI access.
