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

It currently consumes a representative in-memory data gateway whose types mirror stable FoxForge concepts such as printer identity/snapshots, active jobs, faults, material systems, typed capability descriptors, and durable queue states.

The demo gateway is temporary. It remains separated from view rendering so a future public API can replace it without redesigning the screens.

## Frontend composition

`src/app/providers.tsx` owns application-level providers. React Router is the navigation boundary and TanStack Query is the server-state/cache boundary.

`src/data/fleetGateway.ts` currently resolves the representative fleet through TanStack Query. The eventual HTTP client replaces the query function; page components should not know whether data came from demo memory, REST, or cache.

`src/i18n.ts` initializes i18next. English, Russian and Ukrainian are registered from the beginning. Translation coverage is intentionally incremental: the application shell/navigation is localized first, then individual product screens as their copy stabilizes.

Top-level pages are URL-addressable:

- `/`
- `/printers`
- `/queue`
- `/materials`
- `/farm`
- `/system`

## Product structure

The initial navigation is deliberately smaller than Bambuddy, PrintBuddy and PrintOps:

1. **Overview** — fleet KPIs, active jobs, queue pulse and material-system summary.
2. **Printers** — common fleet cards and a printer cockpit/detail surface.
3. **Print queue** — durable queue state including blocked and indeterminate outcomes.
4. **Materials** — capability-driven multi-slot/external material systems.
5. **Farm** — dense operational command-center view for multi-printer use.
6. **System** — user-facing runtime/deployment status and preferences with developer diagnostics kept secondary.

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

Remote application state must enter the frontend through typed query/mutation gateways rather than page-local fetch calls. Pages may keep local presentation state such as an open drawer/tab, but fleet, queue, inventory and printer state belong to the query/data layer.

### Routes are product URLs

Top-level product areas use React Router rather than component-local navigation state. Browser refresh/back/forward navigation must keep the selected product area stable. Printer-specific deep links may be introduced later when the cockpit becomes a full route instead of a modal/detail surface.

### Printer cockpit keeps technical details secondary

The default printer cockpit is user-facing: connection, state, job progress, ETA, layers and loaded materials. Raw capability IDs, adapter names and exact observation timestamps belong in a dedicated **Diagnostics** tab instead of the default printer view.

This keeps the interface useful to normal users without hiding information needed during development and hardware validation.

### Vendor-specific UI mounts through typed capabilities

Deep Bambu controls such as AMS operations, drying, HMS, K profiles, dual-nozzle workflows and Virtual Printer should become capability panels once the corresponding typed domain/application capability exists.

A Moonraker printer must never receive placeholder Bambu controls simply because the Bambu adapter supports them. Empty “vendor extension” placeholders are not rendered; capability panels should appear only when there is real functionality behind them.

### Material systems stay vendor-neutral

The existing `foxforge.material_system` capability is sufficient to render both an AMS-family multi-slot unit and a single external spool. UI copy may display adapter-provided labels (for example `AMS 2 Pro`) while layout and behavior remain based on `MaterialUnitKind`, slots, activity, presence and detected material.

### Queue safety semantics remain visible

The frontend preserves `blocked`, `dispatching`, `accepted`, `indeterminate` and `failed` as distinct states. In particular, `indeterminate` must not be collapsed into a generic failure because it represents a safety-relevant uncertainty about whether printer-side effects occurred.

### Localization starts as infrastructure, not a fork

English, Russian and Ukrainian use one component tree and one set of typed application data. There must not be language-specific page forks. Translation keys are added incrementally as UI copy stabilizes.

### Funding links remain secondary

FoxForge may expose the repository's configured Ko-fi funding destination in the application shell, but it must remain visually secondary to printer controls and operational status. The current UI uses a small low-contrast sidebar-footer link rather than a banner, modal, badge or repeated call-to-action.

## UI refinement pass

The second interface pass makes the foundation more product-like without adding fake backend behavior:

- enlarges the printer detail drawer into a wider cockpit suitable for AMS and future telemetry;
- adds Overview / Materials / Diagnostics tabs inside the cockpit;
- removes raw capability IDs and adapter-oriented explanatory copy from normal user screens;
- keeps exact capability/adapter metadata available under Diagnostics;
- adds user-facing printer summaries for connection, material source and freshness;
- makes the Farm view denser with queue/material context and upcoming-job panels;
- turns System into a user-facing status/deployment/preferences page with developer details collapsed;
- adds a restrained Ko-fi link in the sidebar footer;
- introduces URL routes, TanStack Query and i18next without changing the normalized domain boundary;
- keeps disabled actions disabled until a real API write path exists.

## API integration seam

The intended progression is:

1. expose vendor-independent application reads/writes through an HTTP API;
2. replace the demo query function with a typed REST client;
3. add query mutations for printer/queue/inventory commands;
4. add a WebSocket or SSE event stream for printer snapshots, jobs and queue events and feed updates into the query cache;
5. mount vendor capability panels using descriptors returned by the API.

The backend API must call `FleetService`, `QueueService` and typed capabilities rather than bypassing them to talk directly to adapters.

## Deployment

The frontend builds to static assets. This keeps the runtime suitable for Docker, ARM64 and Umbrel and avoids requiring a separate Node process in production. A later application server/reverse proxy can serve the compiled assets beside the public FoxForge API.

The intended repository-level direction is a clear separation between `backend/`, `frontend/` and `deployment/`; repository-layout migration is tracked separately so it does not couple frontend feature work to Python path moves.

## Acceptance criteria

The UI foundation and refinement pass are acceptable when:

- a production frontend build completes from `frontend/`;
- type checking passes in strict TypeScript mode;
- unit tests validate normalized fleet summary, freshness and material presentation helpers;
- React Router owns top-level product navigation;
- TanStack Query owns the fleet data seam even while it still resolves demo data;
- i18next initializes English, Russian and Ukrainian without language-specific component forks;
- the overview renders a mixed Bambu + Moonraker fleet without vendor payload types;
- the default printer cockpit contains no raw capability IDs or empty vendor placeholders;
- raw adapter/capability metadata remains reachable in the Diagnostics tab;
- the materials view renders both multi-slot and external material-unit shapes;
- the queue view exposes FoxForge queue states without reducing `indeterminate` to `failed`;
- Farm uses the same normalized contracts and exposes queue/material context without vendor branching;
- Ko-fi appears only as a secondary, non-blocking application-shell link;
- responsive layout remains usable on desktop and narrow/mobile widths;
- upstream code provenance is clear: concepts were studied, source was not copied;
- backend Python dependencies remain unchanged.

## Tests

`frontend/src/viewModel.test.ts` covers presentation logic that should remain stable when the demo gateway is replaced by the public API.

`.github/workflows/web-ui.yml` runs:

- dependency installation;
- TypeScript type checking;
- Vitest unit tests;
- Vite production build.

Future API work should add contract tests that serialize backend application/domain objects into the JSON DTOs consumed by this frontend.
