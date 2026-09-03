# Frontend parallel development policy

Status: active development rule

Related: ADR 0001, ADR 0002, `docs/design/web-ui-foundation.md`, `docs/design/inventory-foundation.md`

## Context

FoxForge backend, frontend and deployment work intentionally proceed in parallel. That increases delivery speed, but it also creates a risk that the frontend starts depending on an API, capability, inventory field or queue behavior that exists only in an unmerged branch and later changes before reaching `main`.

The Git repository is the canonical project state. Open pull requests are work in progress, not durable application contracts.

## Decision

Frontend implementation must be **main-driven and gateway-isolated**.

### 1. `main` is the only authoritative backend state

A frontend branch may study active backend work for awareness, but production UI types and behavior must be based on contracts already merged into `main` or on explicitly documented future seams that do not claim to be live.

Open backend pull requests must not be treated as stable API schemas.

### 2. UI branches start from fresh `main`

Every independent UI increment should start from the latest `main` available when the work begins.

Before merge, the UI branch must be updated onto the then-current `main` and its full frontend CI rerun. If backend work merged while the UI branch was open, conflicts are resolved in favor of the merged canonical contracts rather than preserving stale mock assumptions.

### 3. Query/mutation gateways isolate server state

Pages and components must not call future REST endpoints directly.

TanStack Query gateways own the frontend server-state seam. While a backend endpoint is unavailable, the gateway may return representative demo data whose shape is derived from merged domain/design concepts. When the endpoint becomes real, the query function can be replaced without redesigning page components.

Demo DTOs are presentation contracts only. They are never authoritative over Python domain models.

### 4. No fake write behavior

Buttons that require a missing backend mutation remain disabled or explicitly preview-only. The UI must not simulate successful spool edits, printer commands, queue dispatches or material assignments in a way that could be confused with durable application state.

### 5. Vendor depth mounts through capabilities

Common screens consume normalized printer/application read models. Bambu-only or other vendor-only controls are added only when a typed capability exists in merged FoxForge contracts. Frontend work must not infer vendor features from model names, adapter strings or raw protocol payloads.

### 6. Cross-context identifiers remain opaque

Inventory-to-printer assignment uses merged Phase 11 semantics: `printer_id` plus opaque `slot_id`. The UI may resolve a friendly slot label from the current material-system snapshot, but it must not parse `slot_id` to infer AMS/CFS/vendor structure.

Likewise, `spool_id` remains inventory-owned and is not added to printer material snapshots for presentation convenience.

### 7. Keep conflict surfaces small

Parallel UI PRs should primarily modify `frontend/**` and a focused design document. Root README, project-status and broad architecture docs should be changed only when necessary because they are common conflict surfaces for backend work.

## Current inventory example

The Spool Inventory workspace follows these rules:

- the read model is derived from the already-merged Phase 11 inventory design;
- Decimal mass values cross the demo/API boundary as strings and are converted only for display calculations;
- assignments carry `printerId` and opaque `slotId`;
- friendly `X2D Main · A1`-style labels are resolved by matching the opaque slot to the current `MaterialSystemSnapshot`;
- add/move/correct actions remain disabled until public Inventory API mutations exist;
- the inventory gateway is a TanStack Query seam that can later call `InventoryService` HTTP DTOs.

## Merge procedure for a parallel UI PR

1. Confirm the UI branch was created from a real `main` commit.
2. Implement only against merged contracts; document preview-only seams.
3. Run TypeScript checking, unit tests and production build.
4. Immediately before merge, compare with current `main`.
5. If `main` advanced, update the UI branch onto it and preserve newly merged backend/domain work.
6. Rerun the complete Web UI gate on the updated head.
7. Merge only the green, current head.

## Acceptance criteria

A parallel frontend increment is acceptable when:

- it does not depend on unmerged backend implementation details;
- page components consume query/read-model gateways rather than raw vendor/backend transports;
- unavailable mutations are not presented as working actions;
- vendor-specific controls appear only behind merged typed capabilities;
- inventory keeps `spool_id` out of printer material snapshots and treats `slot_id` as opaque;
- the branch has been reconciled with current `main` before merge;
- `npm run check`, `npm test` and `npm run build` pass on the final head.
