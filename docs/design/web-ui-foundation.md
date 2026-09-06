# FoxForge web UI foundation

- **Status:** functional alpha; current `main` includes Pre-Alpha 5 printer-setup/reconnect work
- **Updated:** 2026-09-06

## Purpose

The web UI presents FoxForge-owned application contracts without importing or reconstructing raw vendor protocols. Common screens remain vendor-neutral; deeper vendor panels appear only when typed capabilities exist.

## Stack

- React + TypeScript + Vite;
- React Router;
- TanStack Query;
- i18next / react-i18next;
- native `EventSource` for SSE invalidations;
- responsive CSS for phone, tablet, desktop and ultra-wide layouts.

Normal runtime uses live `/api/v1` models. Demo data is explicit-only through `?demo=1`.

## Current routes

```text
/
/printers
/printers/:printerId
/queue
/materials
/inventory
/farm
/system
```

## Data and command boundaries

Representative seams include:

- fleet/queue/inventory query gateways for canonical HTTP snapshots;
- printer setup client for test/discovery/add/update/remove/reconnect;
- reconnect diagnostics client/read model;
- inventory command client;
- queue artifact/enqueue/dispatch/reconciliation client;
- common job-control client;
- shared command client for explicit Bearer authentication, idempotency and normalized errors;
- realtime bridge for SSE topic -> TanStack Query invalidation.

Frontend code does not receive raw MQTT payloads, Moonraker JSON-RPC objects, Python domain objects, local server paths or printer secrets.

## Printer setup UX

Current source supports:

- one canonical Add Printer entry point;
- Bambu discovery with manual fallback;
- stable/normalized printer identity fields;
- live Test connection;
- Add and Update using backend test-before-save semantics;
- structured normalized setup errors;
- configuration update/remove/reconnect;
- browser behavior that does not persist printer credentials locally.

The UI must not imply a printer was saved when backend preflight failed.

## Reconnect diagnostics

Printer Diagnostics surfaces the secret-safe reconnect read model: failure category, retry state, last attempt/failure and recovery context. It must not display raw adapter exception messages or credentials.

## Realtime model

SSE is an invalidation/replay-resync stream, not a second state database.

- fleet/configuration events invalidate fleet data;
- queue events invalidate queue data;
- inventory events invalidate inventory data;
- `resync_required`, malformed or unknown events fail closed to canonical HTTP refetch;
- frequent updates are batched to avoid uncontrolled refetch storms;
- polling remains an alpha recovery fallback.

## Command model

Operator credentials are explicit and memory-only. Feature clients own typed semantics; the shared command layer only handles cross-cutting authentication/idempotency/error plumbing.

Queue and job-control UI must preserve backend safety:

- queue `dispatchId` is distinct from HTTP `Idempotency-Key`;
- `INDETERMINATE` never becomes a blind retry button;
- job controls require the advertised common capability, a fresh connected snapshot and exact active vendor job identity;
- ambiguous Pause/Resume/Cancel outcomes refresh observation without hidden resend;
- Cancel requires explicit confirmation.

## Materials and inventory

The UI renders normalized material units/slots and treats `slotId` as opaque. Bambu AMS-family units and external feeds can therefore share the common observation view without making AMS a common-domain type.

FoxForge inventory remains separate from physical printer state. Spool assignment associates a FoxForge spool with `printerId + slotId`; the frontend does not parse vendor topology from that slot ID.

## Localization and responsive acceptance

English, Russian and Ukrainian use one component tree with key-parity coverage. Production-browser acceptance exercises representative phone, tablet, 16:9 and 32:9 layouts, including setup/operator-access/runtime regressions.

Alpha 4.3 additionally protects command flows in HTTP/WebKit environments where `crypto.randomUUID()` is absent by installing a secure `crypto.getRandomValues()` UUIDv4 fallback before React renders.

## Vendor-specific UI rule

Deep Bambu controls such as AMS drying, HMS actions, K profiles, dual-nozzle workflows and Virtual Printer must mount through corresponding typed Bambu capabilities. Moonraker must never receive placeholder Bambu controls.

## Acceptance criteria

- live runtime is default; demo mode is explicit;
- TanStack Query owns canonical remote cache state;
- SSE only invalidates/refetchs canonical HTTP state;
- common screens consume FoxForge DTOs, not vendor payloads;
- setup/discovery cannot bypass backend preflight/idempotency;
- reconnect diagnostics remain secret-safe;
- queue/job-control ambiguity never causes automatic side-effect retry;
- material slot IDs stay opaque;
- EN/RU/UK parity and responsive browser gates remain green;
- compiled frontend ships in the unified Python container without a production Node runtime.
