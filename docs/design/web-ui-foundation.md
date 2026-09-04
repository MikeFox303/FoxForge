# FoxForge web UI foundation

**Status:** implemented and evolving beyond the `v0.1.0-alpha.3` released foundation

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

Normal runtime consumes live FoxForge HTTP read models and guarded command APIs. P2 adds a FoxForge-owned SSE invalidation stream while keeping those HTTP read models canonical. Representative demo data remains available only through explicit `?demo=1` mode for documentation/testing; demo objects are not the normal production data source.

## Frontend composition

`src/app/providers.tsx` owns application-level providers. React Router is the navigation boundary and TanStack Query is the server-state/cache boundary.

Current data/command seams include:

- `src/data/fleetGateway.ts` — live fleet and queue reads;
- `src/features/inventory/inventoryGateway.ts` — live spool inventory reads;
- `src/data/realtime.tsx` — P2 EventSource bridge and application-topic → query-family invalidation;
- `src/data/commandClient.ts` — shared browser operator-session/authentication/idempotency/error plumbing;
- `src/data/printerSetupClient.ts` — printer configuration commands;
- `src/features/queue/queueCommandClient.ts` — typed artifact/enqueue/dispatch/reconciliation commands;
- `src/features/printers/jobControlClient.ts` — typed Pause/Resume/Cancel commands against `foxforge.job_control` v1;
- `src/features/printers/JobControlActions.tsx` — capability/state-gated printer cockpit controls and uncertainty UX.

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
2. **Printers** — common fleet cards, printer setup, route-based printer cockpit and typed common job controls.
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

Fleet, queue and inventory reads enter through typed query/data gateways. TanStack Query remains the single browser cache boundary. Command completion and P2 realtime delivery both invalidate/refetch the same canonical HTTP models rather than creating a second presentation state model.

P1 job-control commands invalidate the fleet snapshot after either a conclusive result or an ambiguous outcome. An ambiguous outcome never triggers a hidden command retry; only observation is refreshed.

### P2 realtime is an invalidation stream, not presentation state

`src/data/realtime.tsx` opens one same-origin `EventSource('/api/v1/events')` outside route-specific components. The stream carries FoxForge application topics only:

- `fleet` and `printer_configuration` invalidate the fleet query family;
- `queue` invalidates the queue query family;
- `inventory` invalidates the inventory query family.

`resync_required` invalidates all canonical snapshot families immediately. Unknown or malformed event payloads fail closed to the same full resync.

Frequent `change` events are deduplicated/batched over 250 ms so print-progress telemetry does not create an uncontrolled refetch storm. Periodic polling remains enabled during the alpha stage as recovery fallback while SSE behavior is validated through representative Docker/Umbrel/browser paths.

The browser does not persist its own event history. Standard EventSource `Last-Event-ID` reconnect is handled by the server-side P2 replay contract documented in [realtime-events.md](realtime-events.md).

### Command plumbing is shared; feature semantics are not

`commandClient.ts` owns only cross-cutting browser command concerns:

- operator-session bootstrap;
- bearer-token attachment;
- `Idempotency-Key` header support;
- normalized command errors;
- cached-token reset after HTTP 401.

It must not learn printer-, queue- or inventory-specific business rules. Feature clients remain typed and independent.

For job control, `jobControlClient.ts` owns the P1 request DTO and keeps logical `controlId` separate from HTTP `Idempotency-Key`. `JobControlActions.tsx` owns only presentation/state gating and never translates actions into Bambu or Moonraker commands.

### Routes are product URLs

A printer cockpit is a first-class deep link at `/printers/:printerId`. The route parameter is opaque and resolved against normalized fleet data; routing never infers vendor/model semantics from it.

### Printer cockpit keeps technical details secondary

The default cockpit is user-facing: connection, state, job progress, ETA, layers, materials, common job controls and printer queue context. Raw capability IDs, adapter names and exact observation timestamps belong in Diagnostics.

### Common job controls are capability-driven

Pause/Resume/Cancel render only when `/api/v1/fleet` advertises `foxforge.job_control` v1 for that printer. The UI additionally requires a fresh connected snapshot and the exact active `vendorJobId` before sending a command.

P1 state presentation is:

- `printing` → Pause and Cancel when advertised;
- `paused` → Resume and Cancel when advertised;
- `preparing` → Cancel when advertised;
- stale/offline/no vendor job identity → no actionable device control.

Cancel requires explicit operator confirmation. If the HTTP/device outcome is ambiguous, the control area enters an uncertainty state, refreshes fleet observation and does not automatically resend the side effect. Ordinary telemetry timestamp changes do not by themselves clear the uncertainty lock. See [job-control.md](job-control.md).

### Vendor-specific UI mounts through typed capabilities

Deep Bambu controls such as AMS operations/drying, HMS, K profiles, dual-nozzle workflows and Virtual Printer should become capability panels only after corresponding typed domain/application capabilities exist.

A Moonraker printer must never receive placeholder Bambu controls simply because another adapter supports them. The same rule applies in reverse. Common Pause/Resume/Cancel are shared only because both adapters explicitly implement the same FoxForge capability.

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

The same no-blind-retry principle also applies to ambiguous P1 job-control side effects.

### Localization uses one component tree

English, Russian and Ukrainian share one component/data model. Translation parity tests prevent one locale from silently missing command/safety copy. P1 job-control strings have their own key-parity test in addition to the existing application translation checks.

P2 itself adds no user-facing strings in the first slice because EventSource operation is transparent; any future connection-status UI must preserve the same EN/RU/UK parity discipline.

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
- P1 capability-driven Pause/Resume/Cancel with exact vendor-job targeting;
- P1 ambiguity UX that refreshes observation without blind side-effect replay;
- explicit confirmation before cancelling a print;
- P2 EventSource bridge for fleet/queue/inventory/configuration invalidation;
- P2 replay-gap/restart resync handling through canonical HTTP reads;
- batched high-frequency realtime invalidation plus periodic polling fallback;
- restrained Ko-fi support link;
- responsive/mobile layout.

Still absent until real contracts exist:

- inventory mutation controls for every already-available backend inventory command;
- deeper Bambu capability panels;
- trustworthy automatic material accounting;
- persistent farm scheduling controls;
- distributed/multi-process realtime fan-out beyond the current single-process journal.

## API integration seam

Current layering is:

```text
React views
   |
feature query/command gateways + P2 invalidation bridge
   |
FoxForge REST read DTOs + SSE invalidations + ADR 0004 command DTOs
   |
FleetService / QueueService / InventoryService / typed capabilities
   |
PrinterAdapter implementations
```

The backend API must continue to call application services/capabilities rather than bypassing them to reach adapters.

P2 realtime carries only FoxForge application invalidations and never exposes vendor transport payloads to the frontend. Canonical state still comes from HTTP snapshots.

## Deployment

The frontend builds to static assets and runs inside the unified FoxForge server/container. Production does not require a separate Node process. This keeps deployment suitable for Docker, ARM64 and Umbrel.

The immutable `v0.1.0-alpha.3` image predates P1 and P2. Those source features become available to versioned Docker/Umbrel users only after a later guarded FoxForge release and corresponding Umbrel Store update.

## Acceptance criteria

The current web UI foundation is acceptable when:

- production frontend build and strict TypeScript checking pass;
- Vitest covers stable view/data/command/realtime helper behavior;
- React Router owns product navigation and printer deep links;
- TanStack Query owns remote read/cache state;
- live runtime is the default and demo data requires `?demo=1`;
- EN/RU/UK key parity passes;
- mixed Bambu + Moonraker views use only normalized contracts;
- queue state preserves `INDETERMINATE` instead of reducing it to failure;
- selected print files are staged without leaking client paths;
- queue command UI preserves backend idempotency/reconciliation rules;
- printer setup uses guarded command APIs rather than local mock mutations;
- P1 job controls are rendered from `foxforge.job_control` metadata rather than vendor inference;
- P1 controls require a fresh exact active vendor job identity;
- ambiguous P1 control outcomes never trigger an automatic resend;
- P2 event topics invalidate the correct TanStack Query families;
- P2 `resync_required`, malformed and unknown events fail closed to canonical snapshot refresh;
- realtime progress changes are batched rather than causing unbounded refetches;
- HTTP polling remains a recovery fallback during alpha deployment validation;
- unavailable printer controls are not fabricated;
- responsive layout remains usable on desktop and narrow/mobile widths;
- upstream provenance remains clear;
- unified-container smoke proves compiled UI, API and SSE ship together.

## Tests

`.github/workflows/web-ui.yml` runs:

- dependency installation;
- TypeScript typecheck;
- Vitest unit tests;
- Vite production build.

The unified container workflow independently builds the production application image and smoke-tests server startup/health/UI delivery plus the initial P2 SSE `resync_required` contract.

Queue command client tests cover browser hashing, byte-only staging and separation of durable queue identities from HTTP command idempotency keys. P1 tests cover separation of `controlId` from HTTP idempotency identity, exact job-control request payloads and EN/RU/UK job-control key parity. P2 tests cover topic routing, malformed/unknown fail-closed resync behavior and the backend replay/durable-write/SSE contracts.
