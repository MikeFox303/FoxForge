# FoxForge project status

**Snapshot date:** 2026-09-04  
**Canonical branch:** `main`  
**Published pre-release:** `v0.1.0-alpha.2` (`0.1.0a2`)  
**Umbrel Community App:** `my3d-foxforge` in `MikeFox303/umbrel-3d-printing-store`  
**Maturity:** functional early alpha; architecture and software integration are substantially implemented, while physical-printer validation and several automation/farm features remain incomplete

This file is the concise current-state snapshot. ADRs and design specifications are normative for architecture. Git remains the canonical project state.

## Release versus current code

The currently published build is **`v0.1.0-alpha.2`**. Development has continued after that immutable release, so current `main` contains capabilities that are not yet shipped in the alpha.2 Docker/Umbrel image.

That separation is deliberate: new work lands in `main` through reviewed/validated PRs, then a later guarded release publishes a new immutable image and Umbrel package update.

## Repository architecture

ADR 0002 is implemented:

```text
FoxForge/
├── backend/       Python 3.12+ domain, adapters, services, API and runtime
├── frontend/      TypeScript/React/Vite web application
├── deployment/    Docker and Umbrel deployment contracts/documentation
├── docs/          ADRs, design specifications and status
└── integrations/  isolated migration/provenance material
```

Primary runtime boundary:

```text
React / TypeScript UI
        |
   HTTP API v1
        |
application services
        |
PrinterAdapter + typed capabilities
        |
  +-----+----------------+
  |                      |
Bambu Lab            Moonraker/Klipper
```

Queue, inventory, command security, audit and artifact storage are FoxForge-owned application/runtime concerns rather than vendor-specific code.

## Current `main` capability matrix

| Area | Status | Current boundary |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge identities, normalized snapshots/events/errors, typed capabilities and contract tests. |
| `PrinterAdapter` | Implemented | Vendor-independent common boundary with deep vendor extensions kept outside the lowest-common-denominator contract. |
| Bambu Lab adapter | Software foundation implemented | MQTT/TLS, Bambu project delivery/storage seam, state mapping and execution capability exist; physical X2D validation remains required. |
| Moonraker/Klipper adapter | Software foundation implemented | HTTP/WebSocket, upload/start and normalized state exist; physical OpenKE/Moonraker validation remains required. |
| Fleet service | Implemented | Dynamic add/update/remove/reconnect through `AdapterRegistry` + `FleetService`. |
| Durable print queue | Implemented | SQLite queue state, persisted `dispatch_id`, `DISPATCHING`, `INDETERMINATE`, remote lifecycle and terminal states. |
| Queue retry policy | Implemented | Only explicitly retryable pre-start failures without receipts are eligible; ambiguous or receipt-bearing jobs are never blindly retried. |
| Artifact staging | Implemented | Server-owned content-addressed `/data/artifacts`; streamed SHA-256-verified `.gcode`/`.3mf`; no client-supplied server path. |
| Queue command API | Implemented | Authenticated enqueue, dispatch and explicit reconciliation with durable HTTP idempotency and single-process concurrency guard. |
| Inventory | Durable foundation implemented | Exact `Decimal` ledger, spool metadata, corrections, assignments, archive and SQLite persistence. |
| Inventory command API | Implemented | Authenticated create/correct/empty-mass/move/unassign/archive commands with durable idempotency. |
| Printer configuration API | Implemented | Authenticated test/add/update/remove/reconnect through the live runtime manager. |
| Command security | Implemented foundation | Fail-closed bearer auth, trusted browser command sessions, permissions, request IDs, normalized errors and durable idempotency. |
| Command audit | Implemented | Append-only SQLite audit evidence with request/principal/action/target/outcome and hashed idempotency identity; secrets are not recorded. |
| Public read API | Implemented | `/healthz`, fleet, queue and inventory read models under `/api/v1`. |
| Web UI | Functional alpha | Live fleet/queue/inventory reads, printer management, responsive React UI and `en`/`ru`/`uk`. Full browser print/inventory workflows remain incomplete. |
| Docker runtime | Implemented | Unified backend + compiled SPA image, persistent `/data`, non-root steady state and CI smoke tests. |
| ARM64 delivery | Implemented in release pipeline | Linux `amd64`/`arm64` images are published/smoke-tested in CI; representative Raspberry Pi 5 hardware testing remains required. |
| Umbrel package | Implemented alpha distribution | Community Store package uses authenticated App Proxy, persistent `/data` and immutable FoxForge release image. |
| Realtime API | Not implemented | UI still relies on HTTP snapshots/refetch rather than SSE/WebSocket cache invalidation. |
| Automatic filament accounting | Partial foundation | Durable inventory exists, but automatic reservation/consumption/reconciliation from print jobs is incomplete. |
| Common pause/resume/cancel | Not implemented | Requires a typed common control capability before HTTP/UI exposure. |
| Persistent farm scheduler | Not implemented | Queue runner exists, but durable scheduling/printer-selection/leases are future work. |

## Current command and print path

```text
browser / API client
       |
authenticated command boundary
       |
command audit + HTTP idempotency
       |
artifact staging / queue command
       |
QueueService
       |
PrintExecutionCapability
       |
Bambu or Moonraker adapter
```

Important safety properties:

- clients never provide `/data/...` or another server filesystem path;
- artifact bytes are streamed, size-bounded and verified against SHA-256;
- `queueId` and `dispatchId` are durable explicit identities;
- HTTP `Idempotency-Key` is persisted before queue command side effects;
- same-key replays do not start a second print;
- `DISPATCHING` is persisted before printer submission;
- ambiguous acknowledgement becomes durable `INDETERMINATE`;
- a new dispatch is blocked while reconciliation is required;
- there is no generic blind `retry print` route;
- command audit preflight fails closed before authenticated side effects;
- bearer credentials, printer secrets and raw idempotency keys are not audit fields.

See [`design/queue-command-api.md`](design/queue-command-api.md).

## Inventory status

Inventory is now a real durable bounded context.

Implemented:

- spool identity and metadata;
- initial/remaining/used filament mass with exact `Decimal` accounting;
- editable empty-spool mass;
- purchase date and archive state;
- immutable/idempotent adjustment ledger;
- manual remaining-mass correction;
- one-spool-per-physical-slot assignment constraints;
- opaque printer slot IDs;
- SQLite persistence and restart behavior;
- authenticated mutation endpoints.

Still required for maximum automation:

- queue-time material reservation;
- trustworthy per-material estimates from G-code/3MF;
- completion-driven automatic consumption;
- estimated-versus-actual reconciliation;
- deeper AMS/CFS synchronization and typed vendor-specific material metadata.

## Web UI status

The frontend is no longer a static mock prototype. Current capabilities include:

- React + TypeScript + Vite;
- TanStack Query and route-based application structure;
- live `/api/v1` fleet, queue and inventory reads;
- explicit demo mode rather than silent production mock fallback;
- Overview / Printers / Queue / Materials / Inventory / Farm / System workspaces;
- printer detail cockpit;
- live printer connection/configuration management;
- responsive dark UI;
- English, Russian and Ukrainian localization;
- loading/error/retry/empty states;
- restrained Ko-fi support link;
- frontend typecheck/test/build gates.

The highest-value next UI flow is now:

```text
choose local .gcode/.3mf
        |
calculate SHA-256
        |
authenticated upload
        |
create queue entry
        |
explicit dispatch
        |
show durable lifecycle / reconciliation state
```

Frontend code should consume the backend command contract rather than invent browser-only print state.

## Deployment status

Current deployment is intentionally single-container/single-command-process per installation.

Persistent data:

```text
/data/
├── config.json
├── foxforge.sqlite3
└── artifacts/
```

Properties:

- SPA and API are served by the same process;
- runtime configuration and SQLite state persist in `/data`;
- staged artifacts live outside SQLite but on the same persistent volume;
- command idempotency and audit are restart-safe in SQLite;
- steady-state container execution is non-root;
- Docker/Compose and Umbrel packaging use the same application behavior;
- Linux `amd64` and `arm64` are release targets;
- Umbrel remains behind authenticated App Proxy;
- normal explicit-IP printer use does not require Docker socket, privileged mode or host networking.

The current queue command guard is explicitly **single-process**. Before multiple command workers or distributed nodes are enabled, dispatch/reconciliation serialization must move to a durable database lease/CAS design.

## Physical validation boundary

The largest remaining uncertainty is hardware/runtime behavior, not the common architecture.

### Bambu Lab / X2D

Still needs documented real-device validation for:

- connection and reconnect in the target LAN configuration;
- MQTT state synchronization;
- project upload/storage on X2D;
- print-start acknowledgement and ambiguity handling;
- complete job lifecycle matching;
- AMS 2 Pro material slots and later deep capabilities;
- X2D-specific storage behavior where applicable.

### Moonraker / Ender-3 V3 KE / OpenKE

Still needs documented validation for:

- HTTP/WebSocket connection and reconnect;
- auth/API-key setup;
- G-code upload/checksum/start;
- print lifecycle completion;
- connection-loss/error reconciliation.

### Raspberry Pi 5 / UmbrelOS

Still needs representative hardware validation for:

- install/restart/persistence;
- X2D network reachability from the actual Umbrel environment;
- OpenKE/Moonraker reachability;
- artifact persistence;
- upgrade between immutable FoxForge releases.

Software CI must not be described as physical-printer certification.

## Upstream strategy

ADR 0003 remains the accepted synthesis:

- **Bambuddy** — primary Bambu protocol/behavior reference;
- **PrintBuddy** — primary multi-vendor/provider-isolation reference;
- **PrintOps** — primary operations/farm/scheduling reference;
- **FoxForge** — owns its common printer domain, capability model, queue, inventory, API/frontend contracts and deployment runtime.

FoxForge is not a wholesale fork of any upstream project. Copied or derived material must remain traceable and preserve required notices; newly written FoxForge code remains clearly distinguishable.

## Architecture invariants

1. Common domain/application code does not depend on Bambu or Moonraker transport DTOs.
2. Deep Bambu support is added through typed vendor capabilities rather than weakening the common model.
3. Queue ambiguity is explicit and is never converted into an automatic retry guess.
4. Receipt-bearing jobs are never redispatched by retry logic.
5. Public DTOs never expose printer secrets, raw vendor payloads or local artifact paths.
6. Inventory owns spool identity; printer material snapshots own observed physical material state.
7. Remote mutations remain behind ADR 0004 authentication, authorization, validation, idempotency and audit rules.
8. Docker and Umbrel package the same application behavior rather than separate forks.
9. The current command execution model is single-process; distributed execution requires stronger durable locking.
10. Important architecture/runtime changes are documented in Git rather than treated as chat memory.

## Recommended next sequence

1. **Complete the browser print flow.** Add file selection, client SHA-256, authenticated upload, enqueue/dispatch and clear blocked/failed/indeterminate UI states.
2. **Define artifact retention.** Add garbage-collection rules that cannot delete an artifact still referenced by durable queue/history state.
3. **Run physical validation.** Validate X2D and OpenKE/Moonraker end-to-end before stronger production-readiness claims.
4. **Automate material accounting.** Connect queue completion/material bindings to replay-safe inventory ledger events.
5. **Design common printer controls.** Add typed pause/resume/cancel capability before exposing API/UI controls.
6. **Add realtime delivery.** Define SSE/WebSocket reconnect/replay semantics without replacing snapshot/read contracts.
7. **Build farm scheduling.** Add persistent scheduling/printer-selection on FoxForge capabilities and durable queue state; introduce durable leases before multi-worker execution.

## Assessment

FoxForge has moved beyond an architecture prototype. It now has the core building blocks for a real self-hosted multi-vendor printer manager: two adapter families, durable queue, durable inventory, live UI/API, authenticated configuration/inventory writes, safe artifact staging, idempotent queue commands, command audit and Docker/Umbrel packaging.

It remains an **alpha** because physical validation, full browser print workflows, automatic material accounting, common printer controls, realtime delivery and persistent farm scheduling are not yet complete. The next releases should prioritize end-to-end usability and hardware validation rather than broadening the common abstraction prematurely.
