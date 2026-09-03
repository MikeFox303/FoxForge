# FoxForge web UI foundation

Status: implemented foundation, evolving in pre-alpha

## Purpose

FoxForge needs a user interface that can evolve in parallel with the printer-domain and application layers without coupling presentation code to vendor protocols or forcing common UI screens to understand Bambu/Moonraker payloads.

The frontend lives under `frontend/` and uses the following application stack:

- TypeScript;
- React;
- Vite;
- React Router;
- TanStack Query;
- i18next + react-i18next;
- responsive CSS.

It currently consumes representative in-memory query gateways whose types mirror stable FoxForge concepts such as printer identity/snapshots, active jobs, faults, material systems, typed capability descriptors, durable queue states, and the merged inventory domain.

The demo gateways are temporary. They remain separated from view rendering so future public APIs can replace them without redesigning the screens.

## Frontend composition

`src/app/providers.tsx` owns application-level providers. React Router is the navigation boundary and TanStack Query is the server-state/cache boundary.

`src/data/fleetGateway.ts` currently resolves the representative fleet through TanStack Query. `src/features/inventory/inventoryGateway.ts` does the same for the inventory read model. Eventual HTTP clients replace those query functions; page components should not know whether data came from demo memory, REST, realtime cache updates, or another transport.

`src/i18n.ts` initializes i18next. English, Russian and Ukrainian are registered from the beginning. Translation coverage is intentionally incremental: the application shell/navigation and newer stabilized product screens are localized first, then remaining copy follows as it stabilizes.

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

The navigation is deliberately smaller than Bambuddy, PrintBuddy and PrintOps:

1. **Overview** — fleet KPIs, active jobs, queue pulse and material-system summary.
2. **Printers** — common fleet cards plus a route-based printer cockpit.
3. **Print queue** — durable queue state including blocked and indeterminate outcomes.
4. **Materials** — capability-driven physical multi-slot/external material systems.
5. **Spool inventory** — FoxForge-owned spool state, remaining mass and opaque physical assignments.
6. **Farm** — dense operational command-center view for multi-printer use.
7. **System** — user-facing runtime/deployment status and preferences with developer diagnostics kept secondary.

Additional product areas (archives, files, maintenance, projects, finance/business operations, camera wall, warehouse, etc.) should be added only when FoxForge owns the corresponding domain/application capability rather than cloning another project's navigation breadth prematurely.

## Upstream design influence

Bambuddy, PrintBuddy and PrintOps were reviewed for information architecture and workflow ideas.

Useful patterns retained conceptually:

- printer-first fleet visibility;
- real-time-first status presentation;
- queue and inventory as first-class areas;
- farm-oriented dense monitoring;
- separating general fleet workflows from deeper printer controls.

FoxForge frontend source is newly written. No upstream component, stylesheet or application source was copied into FoxForge.

## Architecture rules

### Common screens consume normalized FoxForge contracts

Printer cards and cockpit views may render identity, connection state, operational state, active job, faults, material systems and advertised capability descriptors. They must not import raw Bambu MQTT payloads, Moonraker JSON responses or adapter implementation modules.

### React Query owns server state

Remote application state must enter the frontend through typed query/mutation gateways rather than page-local fetch calls. Pages may keep local presentation state such as the selected cockpit tab, but fleet, queue, inventory and printer state belong to the query/data layer.

### Routes are product URLs

Top-level product areas use React Router rather than component-local navigation state. Browser refresh/back/forward navigation must keep the selected product area stable.

A printer cockpit is a first-class deep link at `/printers/:printerId`, not only a transient drawer. The `printerId` is encoded as an opaque route parameter and resolved against the current normalized fleet read model; routing must not infer vendor/model semantics from it.

### Printer cockpit keeps technical details secondary

The default route-based printer cockpit is user-facing: connection, state, job progress, ETA, layers, loaded materials and printer-specific queue context. Raw capability IDs, adapter names and exact observation timestamps belong in a dedicated **Diagnostics** tab instead of the default printer view.

This keeps the interface useful to normal users without hiding information needed during development and hardware validation.

### Vendor-specific UI mounts through typed capabilities

Deep Bambu controls such as AMS operations, drying, HMS, K profiles, dual-nozzle workflows and Virtual Printer should become capability panels once the corresponding typed domain/application capability exists in merged FoxForge contracts.

A Moonraker printer must never receive placeholder Bambu controls simply because the Bambu adapter supports them. Empty “vendor extension” placeholders are not rendered; capability panels should appear only when there is real functionality behind them.

### Material systems stay vendor-neutral

The existing `foxforge.material_system` capability is sufficient to render both an AMS-family multi-slot unit and a single external spool. UI copy may display adapter-provided labels (for example `AMS 2 Pro`) while layout and behavior remain based on `MaterialUnitKind`, slots, activity, presence and detected material.

Physical printer material state and FoxForge spool inventory remain separate contexts. Inventory may resolve a friendly physical slot label by matching opaque `printer_id + slot_id`; the UI must not parse `slot_id`, and printer snapshots must not gain `spool_id` for presentation convenience.

### Queue safety semantics remain visible

The frontend preserves `blocked`, `dispatching`, `accepted`, `indeterminate` and `failed` as distinct states. In particular, `indeterminate` must not be collapsed into a generic failure because it represents a safety-relevant uncertainty about whether printer-side effects occurred.

### Localization starts as infrastructure, not a fork

English, Russian and Ukrainian use one component tree and one set of typed application data. There must not be language-specific page forks. Translation keys are added incrementally as UI copy stabilizes.

### Funding links remain secondary

FoxForge may expose the repository's configured Ko-fi funding destination in the application shell, but it must remain visually secondary to printer controls and operational status. The current UI uses a small low-contrast sidebar-footer link rather than a banner, modal, badge or repeated call-to-action.

### Parallel development follows merged main

`docs/design/frontend-parallel-development.md` defines the mandatory rule for UI work that happens while backend work proceeds in parallel: `main` is the only authoritative backend contract state, data access stays behind gateways, unavailable writes remain disabled, and the final UI head is reconciled with current `main` and revalidated before merge.

## UI refinement sequence

The implemented UI refinements make the foundation progressively more product-like without adding fake backend behavior:

- widened the original printer detail surface and moved technical metadata into Diagnostics;
- added React Router, TanStack Query and i18next infrastructure;
- added a restrained Ko-fi link in the sidebar footer;
- added the Spool Inventory workspace from merged Phase 11 semantics;
- moved the printer cockpit to `/printers/:printerId` so it is refreshable, bookmarkable and large enough for future capability panels;
- gave the route-based cockpit Overview / Materials / Queue / Diagnostics tabs using only merged normalized contracts;
- keeps Pause / Stop / Add job and other missing mutations disabled until a real API write path exists;
- keeps temperature, camera, HMS, drying, dual-nozzle and other deeper controls absent until the corresponding typed capability is implemented.

## API integration seam

The intended progression is:

1. expose vendor-independent application reads/writes through an HTTP API;
2. replace demo query functions with typed REST clients;
3. add query mutations for printer/queue/inventory commands;
4. add a WebSocket or SSE event stream for printer snapshots, jobs and queue events and feed updates into the query cache;
5. mount vendor capability panels using descriptors returned by the API.

The backend API must call `FleetService`, `QueueService`, `InventoryService` and typed capabilities rather than bypassing them to talk directly to adapters.

## Deployment

The frontend builds to static assets. This keeps the runtime suitable for Docker, ARM64 and Umbrel and avoids requiring a separate Node process in production. A later application server/reverse proxy can serve the compiled assets beside the public FoxForge API.

The repository layout is already separated into `backend/`, `frontend/` and `deployment/` under ADR 0002 so frontend feature work can evolve independently from Python runtime changes.

## Acceptance criteria

The web UI foundation is acceptable when:

- a production frontend build completes from `frontend/`;
- type checking passes in strict TypeScript mode;
- unit tests validate normalized fleet, inventory and printer-detail presentation helpers;
- React Router owns top-level product navigation and route-based printer deep links;
- TanStack Query owns fleet/inventory data seams even while they still resolve demo data;
- i18next initializes English, Russian and Ukrainian without language-specific component forks;
- the overview renders a mixed Bambu + Moonraker fleet without vendor payload types;
- `/printers/:printerId` resolves normalized printers without parsing vendor identity;
- the default printer cockpit contains no raw capability IDs or empty vendor placeholders;
- raw adapter/capability metadata remains reachable in the Diagnostics tab;
- the materials view renders both multi-slot and external material-unit shapes;
- spool inventory preserves Decimal-string/opaque-slot boundaries from the merged inventory design;
- the queue view exposes FoxForge queue states without reducing `indeterminate` to `failed`;
- Farm uses the same normalized contracts and exposes queue/material context without vendor branching;
- Ko-fi appears only as a secondary, non-blocking application-shell link;
- responsive layout remains usable on desktop and narrow/mobile widths;
- upstream code provenance is clear: concepts were studied, source was not copied;
- backend Python dependencies remain unchanged.

## Tests

`frontend/src/viewModel.test.ts`, inventory presentation tests and printer-detail presentation tests cover logic that should remain stable when demo gateways are replaced by the public API.

`.github/workflows/web-ui.yml` runs:

- dependency installation;
- TypeScript type checking;
- Vitest unit tests;
- Vite production build.

Future API work should add contract tests that serialize backend application/domain objects into the JSON DTOs consumed by this frontend.
