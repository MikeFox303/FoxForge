# Public HTTP API v1 — read foundation

Status: Phase 13 design specification

Related: ADR 0001, ADR 0002, `docs/design/printer-contracts.md`, `docs/design/inventory-foundation.md`, `docs/design/inventory-sqlite.md`

## Context

FoxForge now has stable application services for fleet state, durable queue state and durable inventory state. The web interface is being developed in parallel and currently reads an in-memory demo gateway. The next integration seam must expose FoxForge-owned read models without allowing frontend mock types, SQLite payloads or vendor protocol objects to become the backend contract.

Phase 13 therefore introduces a deliberately small read-only HTTP API. Mutation endpoints and realtime delivery are separate decisions because they require authentication, request validation, command/error semantics and reconnect/replay rules.

## Versioning

The first public namespace is:

```text
/api/v1
```

Every API response also includes:

```text
X-FoxForge-Api-Version: 1
Cache-Control: no-store
```

Collection payloads include `apiVersion: "1"`.

Breaking JSON contract changes require a new API major version. Additive fields may be introduced within v1 when clients are expected to ignore unknown fields.

## Phase 13 endpoints

```text
GET /healthz
GET /api/v1/fleet
GET /api/v1/queue
GET /api/v1/inventory/spools
```

No write endpoint exists in this phase.

The API application receives already-constructed `FleetService`, `QueueService` and `InventoryService` instances from the future composition root. It does not construct concrete Bambu or Moonraker adapters and does not open SQLite directly.

## JSON conventions

Public JSON uses camelCase field names.

Timestamps are UTC ISO 8601 with a `Z` suffix.

Enums use the stable lowercase values already owned by FoxForge domain/application contracts.

Filament mass and inventory fractions are serialized as decimal strings. This preserves exact `Decimal` accounting across JSON/JavaScript boundaries; UI clients may convert them for display but must not round-trip display floats as authoritative accounting values.

Optional values are represented as JSON `null` when the field is part of the stable shape and no value is known.

## Fleet read model

`GET /api/v1/fleet` exposes normalized common printer state only:

- printer identity;
- connection and operational state;
- active normalized job snapshot;
- normalized fault summaries;
- common capability descriptors;
- normalized `MaterialSystemCapability` snapshot when available.

The first capability list reports only common capability IDs and major versions that the API understands. Vendor-specific capability APIs can later use explicit vendor extension namespaces rather than leaking vendor DTOs into the common fleet response.

The fleet response must not expose MQTT topics, access codes, FTPS paths, Moonraker URLs, raw HMS payloads or other transport/vendor internals.

## Queue read model

`GET /api/v1/queue` exposes the durable queue state machine, including the full backend lifecycle:

```text
pending
blocked
dispatching
accepted
preparing
printing
paused
completed
cancelled
indeterminate
failed
```

This is intentionally broader than the initial frontend mock type, which was created before Phase 9 lifecycle tracking. The public API follows the canonical backend state machine; the frontend should update its client type instead of the API discarding real states.

Queue responses may expose safe artifact metadata such as artifact ID, filename, format, size and SHA-256. They must never expose the local server filesystem `path` from `LocalPrintArtifact`.

The queue read model also includes assessment, receipt and normalized error information needed to explain blocked, accepted and uncertain jobs without exposing vendor exception objects.

## Inventory read model

`GET /api/v1/inventory/spools` exposes:

- stable spool ID;
- material/manufacturer/product/color metadata;
- initial, remaining and used filament mass;
- used fraction;
- editable empty-spool mass;
- purchase date;
- archive state;
- current physical assignment when present.

The assignment contains `printerId` and opaque `slotId`. The API does not infer AMS/CFS/vendor semantics from the slot identifier.

Inventory SQLite payload shape and schema version are not public API contracts.

## Health endpoint

`GET /healthz` reports that the HTTP process can serve requests and identifies API version 1.

Phase 13 does not claim that every configured printer is online or physically validated. Deeper readiness/liveness semantics may be added separately when the production composition root and deployment packaging exist.

## Frontend integration boundary

The parallel React UI currently uses `frontend/src/data/fleetGateway.ts` and mock data. The intended migration is:

```text
React query/hooks
      |
frontend typed API client
      |
GET /api/v1/...
      |
FoxForge API read models
      |
application services
```

Frontend TypeScript interfaces may mirror the public API, but they are not imported into Python and do not define backend persistence or domain models.

Phase 13 intentionally does not edit `frontend/**`, root `README.md` or `docs/README.md`, avoiding conflicts with the parallel UI branch.

## Origin and browser policy

No wildcard CORS policy is enabled by the API foundation.

The preferred deployment is same-origin through the FoxForge reverse proxy/application server. If cross-origin deployments become a supported product requirement, allowed origins and credential policy must be configured explicitly rather than enabling permissive `*` behavior by default.

## Security boundary

Read-only does not mean public-to-the-Internet by design. Authentication/authorization belongs in the production server/deployment boundary and is not implemented by Phase 13.

For that reason Phase 13 deliberately does **not** add:

- print start/cancel/pause commands;
- queue enqueue/retry/reconcile commands;
- inventory add/edit/assign/consume commands;
- printer credential/configuration endpoints.

Those mutations require a separate contract for auth, validation, idempotency and normalized HTTP errors.

## Realtime boundary

Phase 13 is snapshot/read-only HTTP. It does not expose WebSocket or SSE streams.

A later realtime phase should consume normalized application/fleet events and define reconnect/replay semantics independently from the request/response DTOs. The frontend can begin by polling/refetching the read endpoints and later add event-driven cache invalidation without changing the core snapshot shapes.

## Acceptance criteria

- API v1 is under `/api/v1` and health remains `/healthz`;
- read handlers depend only on application/common contracts;
- API production code imports no concrete Bambu or Moonraker adapter packages;
- fleet JSON contains normalized common state and material systems;
- queue JSON contains the full canonical lifecycle state machine;
- local artifact filesystem paths are never serialized;
- inventory mass values round-trip as exact decimal strings;
- timestamps are UTC ISO 8601 with `Z`;
- responses are `no-store` and expose API version headers;
- no wildcard CORS is enabled;
- no mutation endpoint is added;
- frontend files are untouched;
- Ruff, formatting and the full backend suite pass on Python 3.12 and 3.13.

## Next implementation direction

After the read API is merged, the parallel frontend can replace its demo gateway with a typed v1 client and update its queue state union to the full backend lifecycle. Realtime cache invalidation should follow as a separate phase. Mutation APIs should be designed only after authentication and normalized HTTP command/error semantics are recorded.
