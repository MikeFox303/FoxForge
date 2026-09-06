# FoxForge interface refactor direction

- **Status:** design direction; not yet an implementation claim
- **Updated:** 2026-09-06
- **Milestone relevance:** Pre-Alpha 5 scoped UI work plus post-Alpha-5 follow-up

This document records the current FoxForge interface direction so the design does not live only in chat history. It complements [web-ui-foundation.md](web-ui-foundation.md) and [upstream-adoption-map.md](upstream-adoption-map.md). Backend/domain safety contracts remain authoritative where UI convenience conflicts with them.

## Upstream references reviewed

The interface direction is **inspired** by the following upstream projects. The intended FoxForge implementation is newly written against FoxForge API/capability contracts; this document does not authorize copying upstream frontend code without a separate provenance record.

- Bambuddy — `maziggy/bambuddy` at `9b2c49d866ae1ddc63f23cea53461ff19cb86346`
- PrintBuddy — `vmhomelab/printbuddy` at `b9f81c7a9a5fae861daf2e91737e4e978db8aa5e`
- PrintOps — `ichwars/PrintOps` at `d8b3b220ab987ec2bbbd2d93838b7144cc0257e1`

Reference roles:

- **Bambuddy:** dense Bambu printer cards, AMS/material presentation, quick printer actions and deep printer-control ergonomics.
- **PrintBuddy:** multi-vendor presentation, responsive/mobile ergonomics and flexible sidebar behavior.
- **PrintOps:** information architecture for a growing application, grouped navigation and operations-oriented dashboards.
- **FoxForge:** keep its own dark visual identity, orange accent, capability-driven architecture, security semantics and vendor-independent common surfaces.

## Design goals

1. Make printer state understandable at a glance without requiring several detail-page clicks.
2. Reduce large empty surfaces and improve information density on desktop/ultrawide displays.
3. Keep the interface usable on phone/tablet without horizontal overflow or tiny controls.
4. Preserve deep Bambu functionality without putting Bambu protocol fields into generic UI code.
5. Let generic screens render from FoxForge read models and typed capabilities; vendor extensions mount only when advertised.
6. Keep operator authentication, idempotency, stale-job guards and `INDETERMINATE` semantics unchanged by visual refactoring.
7. Keep semantic status colors separate from the FoxForge orange brand accent.

## Visual identity

FoxForge should remain visually distinct rather than becoming a Bambuddy/PrintBuddy/PrintOps skin.

Preferred baseline:

- dark first, with later Light/System/OLED variants;
- FoxForge orange as the brand/action accent;
- green = healthy/success, amber = warning, red = error/danger, blue = informational/active telemetry regardless of accent;
- compact cards, clear hierarchy, restrained shadows/gradients;
- real icons instead of two-letter navigation placeholders where practical;
- typography and spacing optimized for operational dashboards rather than marketing pages.

## Navigation direction

Current top-level areas can remain simple during Pre-Alpha 5, but the shell should be ready for grouped navigation as the product grows.

Near-term:

```text
Overview
Printers
Print Queue
Materials
Spools
Farm
System
```

Long-term grouping concept:

```text
Overview

Production
  Printers
  Queue
  Farm

Materials
  Spools
  Materials

Library
  Files
  Archives
  Projects

System
```

The sidebar should support expanded and compact states on desktop and a drawer/suitable mobile navigation pattern on smaller screens. Do not add every future feature as a permanent top-level row.

## Printer list direction

Printer cards should become operational summaries rather than mostly navigation containers.

A standard card should be able to show, when the corresponding capabilities exist:

- vendor/model/name;
- online/idle/printing/paused/error state;
- active job, progress and remaining time;
- representative temperatures;
- compact material-source summary;
- queue count;
- concise connection freshness;
- safe quick actions that are valid for the exact observed job.

Target density modes:

- **Compact:** farm overview / many printers.
- **Standard:** default balance of telemetry and actions.
- **Detailed:** richer material/control/camera context when implemented.

Unsupported data must be absent/unknown, never fabricated from the model name.

## Printer detail direction

Target capability-driven tabs:

```text
Overview
Control
Materials
Queue
Diagnostics
```

Tabs/sections should appear only when the necessary common or vendor-specific capabilities exist.

Generic screens must not contain `model == "X2D"` feature switches. Bambu-only controls such as AMS drying, HMS actions, K profiles, dual-nozzle routing or future Virtual Printer controls belong under typed Bambu capability boundaries.

## X2D material topology direction

The material UI must represent physical routing, not only a flat list of trays.

Physical acceptance fixture from the current X2D test setup:

```text
X2D
├─ AMS 2 Pro
│  ├─ A1 PETG
│  ├─ A2 PETG
│  ├─ A3 PETG
│  └─ A4 PETG
├─ External Left  -> left nozzle  -> currently empty
└─ External Right -> right nozzle -> PLA
```

The UI should preserve the distinction between:

- AMS/AMS 2 Pro/AMS HT hardware identity;
- physical source/tray identity;
- left/right toolhead routing on dual-nozzle hardware;
- FoxForge inventory spool identity.

Do not permanently encode `AMS -> one nozzle` as a universal truth: future Filament Track Switch routing can make the graph dynamic.

## Add Printer direction

Move from one dense technical form toward a staged flow while retaining manual fallback:

1. choose provider/family;
2. discover candidates or enter a host manually;
3. select/confirm model and identity when needed;
4. enter credentials;
5. run structured connectivity diagnostics;
6. persist only after backend preflight passes.

Normal users should not need to invent a FoxForge internal printer ID. Discovery remains candidate-only and cannot bypass authenticated test-before-save semantics.

## Operator access direction

Keep the current security model, but reduce permanent visual noise in the top bar.

A compact lock/shield state can expose the detailed Operator Access panel on demand. The credential remains explicit and memory-only; reload must still drop write access. No UI refactor may introduce token persistence, tokenless bootstrap or hidden automatic unlock.

## Frontend structure direction

Continue moving from a large root component and feature-specific CSS toward reusable primitives and feature boundaries. Suggested shape (exact names may evolve):

```text
frontend/src/
├── app/
│   ├── AppShell.tsx
│   ├── AppRoutes.tsx
│   └── providers.tsx
├── ui/
│   ├── Button.tsx
│   ├── IconButton.tsx
│   ├── Card.tsx
│   ├── Badge.tsx
│   ├── Tabs.tsx
│   ├── Modal.tsx
│   ├── Drawer.tsx
│   ├── Tooltip.tsx
│   ├── Progress.tsx
│   ├── EmptyState.tsx
│   ├── FormField.tsx
│   ├── StatusIndicator.tsx
│   └── PageHeader.tsx
├── features/
│   ├── printers/
│   ├── queue/
│   ├── materials/
│   ├── inventory/
│   └── farm/
├── vendor/
│   └── bambu/
└── styles/
    ├── tokens.css
    ├── layout.css
    └── responsive.css
```

Do not introduce a large UI framework merely to perform the refactor. Reusable FoxForge primitives plus the existing React/TypeScript/CSS stack are sufficient unless a later ADR justifies otherwise.

## Pre-Alpha 5 UI scope

The UI work allowed to affect the Alpha 5 milestone should stay focused on the Bambu physical-control path:

1. App shell/sidebar/topbar cleanup.
2. Printer cards with better information density.
3. X2D printer detail hierarchy.
4. X2D/AMS 2 Pro + dual external-feed material presentation.
5. Add Printer/discovery workflow improvements.
6. Operator Access presentation cleanup without security changes.
7. RU/UK/EN localization cleanup, including relative-time strings.
8. Responsive/mobile/ultrawide polish for the affected screens.

Defer broad redesigns of future Library/Archives/Statistics/Maintenance/advanced Farm screens until after the Alpha 5 physical print gate unless a blocking usability defect requires them.

## Acceptance criteria

For the scoped Pre-Alpha 5 interface refactor:

- a real X2D card shows useful state without excessive empty space;
- X2D material UI can show AMS 2 Pro with four PETG slots plus both external feeds, including External Right = PLA and External Left = empty for the current physical fixture;
- left/right toolheads are not conflated;
- the UI identifies AMS 2 Pro when native metadata proves that hardware type;
- generic UI does not infer Bambu-only functionality solely from a model string;
- Add Printer remains test-before-save and supports discovery plus manual fallback;
- Operator Access remains memory-only and fail-closed;
- EN/RU/UK have no obvious mixed-language strings in the affected flows;
- phone 390x844, tablet 900x1024, desktop 1920x1080 and ultrawide 5120x1440 remain free of blocking layout regressions;
- primary touch targets are approximately 44px or larger where practical;
- focus visibility and non-color status cues remain usable;
- existing backend command/idempotency/job-control safety contracts are unchanged.

## Required tests

At minimum, add/extend:

- Vitest coverage for AppShell/navigation, printer card states, capability-gated detail sections, material topology presentation, Add Printer flow and localization;
- Playwright production-container acceptance at the existing phone/tablet/desktop/ultrawide viewports;
- deterministic frontend fixtures for a dual-nozzle X2D with AMS 2 Pro and two external feeds;
- regression tests ensuring unsupported/vendor-only controls do not appear for adapters that do not advertise the capability.

Physical UI acceptance still requires the real Raspberry Pi 5 + Umbrel + X2D path; browser fixtures do not prove hardware behavior.

## Provenance classification

Current classification for this design direction: **inspired**.

If later implementation copies or materially derives upstream frontend code, that PR must record repository, exact commit, path, license, destination, classification and preserved notices according to [upstream-adoption-map.md](upstream-adoption-map.md).
