# FoxForge web UI foundation

**Status:** implemented and evolving from the `v0.1.0-alpha.3` released foundation

## Purpose

FoxForge needs a user interface that can evolve in parallel with printer/application work without coupling presentation code to vendor protocols or forcing common screens to understand Bambu/Moonraker payloads.

The frontend lives under `frontend/` and uses:

- TypeScript;
- React;
- Vite;
- React Router;
- TanStack Query;
- i18next + react-i18next;
- responsive CSS.

Normal runtime consumes live FoxForge HTTP read models and guarded command APIs. Representative demo data remains available only through explicit `?demo=1` mode for documentation/testing; demo objects are not the normal production data source.

## Frontend composition

`src/app/providers.tsx` owns application-level providers. React Router is the navigation boundary and TanStack Query is the server-state/cache boundary.

Current data/command seams include:

- `src/data/fleetGateway.ts` — live fleet and queue reads;
- `src/features/inventory/inventoryGateway.ts` — live spool inventory reads;
- `src/data/commandClient.ts` — shared browser operator-session/authentication/idempotency/error plumbing;
- `src/data/printerSetupClient.ts` — printer configuration commands;
- `src/features/queue/queueCommandClient.ts` — typed artifact/enqueue/dispatch/reconciliation commands.

Feature components do not receive raw Bambu MQTT payloads, Moonraker JSON-RPC responses, Python domain objects or local server paths.

Top-level and printer-detail pages are URL-addressable:

- `/`
- `/printers`
- `/printers/:printerId`
- `/queue`
- `/materials`
- `/inventory`
- `/farm`
- `/system`

## Product structure

1. **Overview** — fleet KPIs, active jobs, queue pulse and material-system summary.
2. **Printers** — common fleet cards, printer setup and route-based printer cockpit.
3. **Print queue** — durable queue state plus safe file staging/enqueue/dispatch/reconciliation.
4. **Materials** — capability-driven physical multi-slot/external material systems.
5. **Spool inventory** — FoxForge-owned spool state, remaining mass and opaque physical assignments.
6. **Farm** — dense operational command-center view for multi-printer use.
7. **System** — runtime/deployment status, language and diagnostics.

Additional areas should be added only when FoxForge owns the corresponding domain/application capability rather than cloning another project's navigation breadth.

## Upstream design influence

Bambuddy, PrintBuddy and PrintOps are reviewed for information architecture and workflow ideas:

- Bambuddy for deep Bambu behavior/product workflows;
- PrintBuddy for multi-vendor/provider isolation;
- PrintOps for queue/farm/operations patterns.

FoxForge frontend source is newly written. Upstream components/styles/application source are not copied into FoxForge unless explicitly documented with compatible provenance/license treatment.

## Architecture rules

### Common screens consume normalized FoxForge contracts

Printer cards/cockpits may render identity, connection state, operational state, active job, faults, material systems, queue state and advertised capabilities. They must not import raw vendor transports or adapter implementation modules.

### TanStack Query owns remote read state

Fleet, queue and inventory reads enter through typed query/data gateways. Query invalidation/refetch is the current synchronization mechanism after commands. Future realtime delivery should update the same cache instead of creating a second presentation state model.

### Command plumbing is shared; feature semantics are not

`commandClient.ts` owns only cross-cutting browser command concerns:

- operator-session bootstrap;
- bearer-token attachment;
- `Idempotency-Key` header support;
- normalized command errors;
- cached-token reset after HTTP 401.

It must not learn printer-, queue- or inventory-specific business rules. Feature clients remain typed and independent.

### Routes are product URLs

A printer cockpit is a first-class deep link at `/printers/:printerId`. The route parameter is opaque and resolved against normalized fleet data; routing never infers vendor/model semantics from it.

### Printer cockpit keeps technical details secondary

The default cockpit is user-facing: connection, state, job progress, ETA, layers, materials and printer queue context. Raw capability IDs, adapter names and exact observation timestamps belong in Diagnostics.

### Vendor-specific UI mounts through typed capabilities

Deep Bambu controls such as AMS operations/drying, HMS, K profiles, dual-nozzle workflows and Virtual Printer should become capability panels only after corresponding typed domain/application capabilities exist.

A Moonraker printer must never receive placeholder Bambu controls simply because another adapter supports them.

### Material systems stay vendor-neutral

`foxforge.material_system` is sufficient to render both an AMS-family multi-slot unit and a single external spool. UI layout/behavior is based on normalized units/slots/activity/presence/detected material.

Inventory identity remains separate. The UI may associate an opaque `printer_id + slot_id` with a FoxForge spool, but it must not parse `slot_id` or force `spool_id` into printer snapshots.

### Queue safety semantics remain visible

`PENDING`, `BLOCKED`, `DISPATCHING`, `ACCEPTED`, lifecycle states, `FAILED` and `INDETERMINATE` remain distinct.

The browser queue workflow follows [queue-command-ui.md](queue-command-ui.md):

- hash the selected file in browser;
- stage bytes + expected hash, never a client path;
- enqueue separately from dispatch;
- keep queue `dispatch_id` distinct from HTTP idempotency identity;
- preserve the same HTTP key across an uncertain replay of one command;
- use a new HTTP key after a conclusive `BLOCKED`/retryable pre-start failure when the operator intentionally tries again;
- never expose blind retry for `INDETERMINATE`;
- expose failed-entry retry only when backend read state marks it retryable.

### Localization uses one component tree

English, Russian and Ukrainian share one component/data model. Translation parity tests prevent one locale from silently missing command/safety copy.

### Funding links remain secondary

Ko-fi remains a small sidebar-footer link, not a banner/modal or repeated operational distraction.

### Parallel development follows merged main

`frontend-parallel-development.md` remains mandatory: `main` is the authoritative backend contract; feature branches reconcile with current `main` before merge; unavailable capabilities must not be fabricated.

## Implemented refinement sequence

The UI has progressed from static/demo foundation to functional alpha:

- route-based printer cockpit and diagnostics separation;
- TanStack Query/i18next/React Router infrastructure;
- live fleet, queue and inventory reads in normal runtime;
- explicit loading/refresh/recoverable-error states;
- truthful stale/degraded/offline presentation;
- printer configuration launcher/dialog using authenticated commands;
- shared browser command-session infrastructure;
- safe queue file hashing/staging/enqueue/dispatch workflow;
- explicit blocked/retryable failure semantics;
- explicit `INDETERMINATE` started/not-started reconciliation;
- restrained Ko-fi support link;
- responsive/mobile layout.

Still absent until real contracts exist:

- common pause/resume/cancel UI;
- realtime WebSocket/SSE delivery;
- inventory mutation controls for every already-available backend inventory command;
- deeper Bambu capability panels;
- trustworthy automatic material accounting;
- persistent farm scheduling controls.

## API integration seam

Current layering is:

```text
React views
   |
feature query/command gateways
   |
FoxForge REST read DTOs + ADR 0004 command DTOs
   |
FleetService / QueueService / InventoryService / typed capabilities
   |
PrinterAdapter implementations
```

The backend API must continue to call application services/capabilities rather than bypassing them to reach adapters.

Future realtime delivery should carry FoxForge application events and update TanStack Query caches; it must not expose vendor transport payloads to the frontend.

## Deployment

The frontend builds to static assets and runs inside the unified FoxForge server/container. Production does not require a separate Node process. This keeps deployment suitable for Docker, ARM64 and Umbrel.

## Acceptance criteria

The current web UI foundation is acceptable when:

- production frontend build and strict TypeScript checking pass;
- Vitest covers stable view/data/command helper behavior;
- React Router owns product navigation and printer deep links;
- TanStack Query owns remote read/cache state;
- live runtime is the default and demo data requires `?demo=1`;
- EN/RU/UK key parity passes;
- mixed Bambu + Moonraker views use only normalized contracts;
- queue state preserves `INDETERMINATE` instead of reducing it to failure;
- selected print files are staged without leaking client paths;
- queue command UI preserves backend idempotency/reconciliation rules;
- printer setup uses guarded command APIs rather than local mock mutations;
- unavailable printer controls are not fabricated;
- responsive layout remains usable on desktop and narrow/mobile widths;
- upstream provenance remains clear;
- unified-container smoke proves compiled UI and API still ship together.

## Tests

`.github/workflows/web-ui.yml` runs:

- dependency installation;
- TypeScript typecheck;
- Vitest unit tests;
- Vite production build.

The unified container workflow independently builds the production application image and smoke-tests server startup/health/UI delivery.

Queue command client tests cover browser hashing, byte-only staging and separation of durable queue identities from HTTP command idempotency keys. Translation parity tests cover EN/RU/UK command copy.
