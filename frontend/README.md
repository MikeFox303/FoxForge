# FoxForge web UI

The frontend is the React/TypeScript web application shipped inside the unified FoxForge runtime.

## Stack

- TypeScript;
- React;
- Vite;
- React Router;
- TanStack Query;
- i18next + react-i18next;
- responsive CSS;
- native `EventSource` for FoxForge SSE invalidations.

Normal runtime uses live FoxForge `/api/v1` models. Representative demo data is available only through explicit `?demo=1` mode and is not the normal production data source.

## Current product areas

- fleet overview;
- printer list and route-based printer cockpit;
- Add/Update/Remove/Reconnect printer setup;
- Bambu discovery plus manual setup fallback;
- normalized setup error presentation;
- per-printer reconnect diagnostics;
- durable print queue with browser hashing/staging/enqueue/dispatch/reconciliation;
- common capability-driven Pause/Resume/Cancel;
- physical material-system views for AMS-family and external sources;
- spool inventory create/correct/empty-mass/assign/move/unassign/archive/history workflows;
- system/deployment information;
- English, Russian and Ukrainian localization.

TanStack Query remains the canonical browser cache boundary. SSE carries invalidations/replay-resync signals; authoritative state is refetched from HTTP snapshots.

## Security boundary

Protected writes require the explicit FoxForge operator credential. The browser stores it only in memory for the current tab and clears it on Lock, authentication failure or page/tab lifecycle. UI code must not weaken backend idempotency/reconciliation semantics or fabricate vendor capabilities.

## Run locally

```bash
cd frontend
npm ci
npm run dev
```

## Validate

```bash
npm run check
npm test
npm run build
```

The production build is emitted to `frontend/dist/` and served by the Python runtime; production deployment does not require a separate Node.js process.

See [`../docs/design/web-ui-foundation.md`](../docs/design/web-ui-foundation.md).
