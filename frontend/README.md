# FoxForge web UI

This directory contains the FoxForge web interface foundation.

The frontend stack is:

- TypeScript;
- React;
- Vite;
- React Router for URL-addressable application views;
- TanStack Query for the frontend data-access/cache boundary;
- i18next + react-i18next for localization;
- responsive CSS suitable for desktop, tablet and narrow/mobile layouts.

The current data gateway still returns representative in-memory data that mirrors FoxForge's normalized printer, material-system and queue concepts. It does not import backend Python modules or vendor protocol payloads.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

Vite will print the local development URL.

## Validate

```bash
npm run check
npm test
npm run build
```

The production build is emitted to `frontend/dist/`.

## Application structure

`src/app/providers.tsx` owns application-level providers such as TanStack Query and React Router.

`src/data/fleetGateway.ts` is the temporary server-state seam. It currently resolves demo data through TanStack Query. When the backend HTTP API exists, the query function should be replaced with the typed API client rather than changing page components.

`src/i18n.ts` initializes the localization layer and currently provides shell/navigation strings for English, Russian and Ukrainian. Translation coverage will expand incrementally rather than blocking core interface development.

The UI currently provides:

- fleet overview;
- printer cards and a wider printer cockpit with Overview / Materials / Diagnostics tabs;
- durable print-queue view;
- material-system view for multi-slot and external spool units;
- farm command-center view;
- user-facing system/deployment information with developer diagnostics collapsed by default;
- a restrained optional Ko-fi support link in the sidebar footer.

The public FoxForge API and real-time transport are not implemented yet. The intended next boundary is REST for reads/writes plus WebSocket or SSE for live printer/queue events.

See [`docs/design/web-ui-foundation.md`](../docs/design/web-ui-foundation.md) for the architectural rules, upstream design provenance, acceptance criteria and migration path.
