# Public HTTP API v1

- **Status:** implemented and actively used by the web UI
- **Updated:** 2026-09-06
- **Related:** ADR 0001, ADR 0004, ADR 0005

## Boundary

FoxForge HTTP handlers expose application/domain DTOs only. They receive already-constructed services from the runtime composition root and do not construct vendor adapters or open persistence directly.

```text
browser / automation client
          |
       /api/v1
          |
application services + typed capabilities
          |
 persistence / PrinterAdapter implementations
```

Breaking JSON contract changes require a new API major version. Public JSON uses camelCase, UTC ISO-8601 timestamps and exact decimal strings for inventory mass values.

## Read surfaces

Current read models include the established fleet, queue and inventory snapshots plus configuration/diagnostic surfaces required by the current application.

Core reads include:

```text
GET /healthz
GET /api/v1/fleet
GET /api/v1/queue
GET /api/v1/inventory/spools
GET /api/v1/events
GET /api/v1/diagnostics/reconnect
```

Additional `/api/v1` routes support configuration, artifacts and inventory/history according to their design documents.

Read DTOs never expose printer credentials, raw vendor payloads or local artifact filesystem paths.

## Fleet model

Fleet responses expose normalized identity, connection/operational state, active job, faults, common capability descriptors and normalized material-system snapshots when available.

Vendor-specific capability APIs may coexist with the common surface, but raw Bambu/Moonraker transport objects do not enter the common fleet DTO.

## Queue model

The API preserves the durable lifecycle rather than flattening uncertain states:

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

Safe artifact metadata may be exposed; server-local artifact paths are not.

## Inventory model

Inventory reads expose FoxForge spool metadata, exact mass values, archive state, history and opaque physical assignment (`printerId + slotId`). SQLite rows/schema are not public API contracts.

## Commands

Mutation APIs are implemented behind ADR 0004/0005 and feature-specific design contracts. They use:

- explicit application authentication;
- permission checks;
- request IDs;
- durable HTTP idempotency where required;
- normalized errors;
- append-only command audit;
- typed feature DTOs rather than a generic vendor-command escape hatch.

Major command families include printer setup, artifact/queue operations, inventory mutations and common job control.

## Realtime

`GET /api/v1/events` is an SSE invalidation/replay-resync layer. It never becomes an alternate source of canonical state. Clients refresh the HTTP snapshot after relevant events or `resync_required`.

## Security and origin

Same-origin deployment is preferred. Wildcard CORS is not enabled by default. Read availability does not imply Internet exposure is recommended.

Protected writes require the explicit FoxForge command credential. Printer setup read models expose only secret-configured booleans; secrets are write-only from the client perspective.

## API invariants

- application/common code defines public DTO semantics;
- vendor protocol DTOs never leak into common responses;
- local server paths and credentials are never serialized;
- inventory decimal values remain exact across JSON boundaries;
- mutation handlers cannot bypass application services/typed capabilities;
- ambiguous printer side effects preserve reconciliation-required semantics;
- SSE carries invalidations rather than authoritative printer/queue/inventory state.

## Validation

API changes require applicable backend tests plus frontend/container/browser/deployment-auth gates. Physical printer behavior remains a separate evidence requirement and is not inferred from HTTP contract tests.
