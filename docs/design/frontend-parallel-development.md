# Frontend parallel development policy

- **Status:** active development rule
- **Updated:** 2026-09-06
- **Related:** [ADR 0001](../adr/0001-printer-adapter-architecture.md), [ADR 0002](../adr/0002-repository-layout.md), [web UI](web-ui-foundation.md)

FoxForge backend, frontend and deployment work may proceed in parallel, but `main` is the only durable implementation state. Open PRs are work in progress, not public contracts.

## Rules

### Main-driven contracts

Production UI types/behavior are based on contracts already merged into `main`. A frontend branch may study active backend work for awareness but must not present an unmerged API/capability as live functionality.

Before merge, update the branch against then-current `main` and rerun the complete applicable frontend/browser gate.

### Gateway isolation

TanStack Query/feature clients own server-state boundaries. Page components consume typed FoxForge read/command models rather than raw HTTP/vendor payloads.

Explicit `?demo=1` data is presentation-only and must not become authoritative over backend/domain contracts.

### No fake writes

If a backend mutation/capability does not exist, the UI must not simulate successful durable state. Preview-only or unavailable behavior must be explicit.

Conversely, once a mutation is implemented, documentation and UI must stop describing it as unavailable. Current inventory create/correct/empty-mass/assignment/archive/history commands, printer setup commands, queue commands and common job control are real command surfaces.

### Capability-driven vendor depth

Generic UI uses FoxForge common models. Vendor-only controls appear only behind the corresponding typed vendor capability; code must not infer Bambu behavior from display names/model strings/raw fields.

### Opaque cross-context identity

Inventory assignment uses `printerId + slotId`. `slotId` is opaque outside the printer adapter; the frontend may resolve a friendly current label but must not parse AMS/CFS topology from the string. `spoolId` stays inventory-owned.

### Keep conflict surfaces small

Parallel feature PRs should focus on their feature area. Root README/project-status/ADRs change only when the durable project contract actually changes.

## Current inventory example

The inventory UI now uses live `/api/v1` read/command surfaces for the normal operator workflow. Exact mass crosses JSON as decimal strings, assignments keep opaque `slotId`, and friendly printer/material labels are derived from current FoxForge read models.

Automatic consumption/reservation remains separate frozen P3 work and must not be simulated in the normal inventory UI.

## Merge checklist

1. branch from/refresh against real `main`;
2. implement only merged/live contracts or explicitly marked preview seams;
3. keep feature access behind typed gateway/capability boundaries;
4. run `npm run check`, `npm test`, `npm run build` plus applicable production-browser acceptance;
5. reconcile again if `main` advanced before merge;
6. merge only the current green head.
