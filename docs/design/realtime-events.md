# Realtime application events

**Status:** implemented in P2 development source  
**Transport:** Server-Sent Events (SSE)  
**Endpoint:** `GET /api/v1/events`

## Context

FoxForge already normalizes Bambu and Moonraker state behind `PrinterAdapter`, `FleetService`, queue and inventory application services. The browser currently polls HTTP snapshots. P2 adds realtime delivery without exposing Bambu MQTT messages, Moonraker WebSocket payloads or vendor transport lifecycle to frontend code.

The realtime stream is intentionally an **application invalidation stream**, not a second source of truth. Canonical state remains the versioned HTTP read models such as `/api/v1/fleet`, `/api/v1/queue` and `/api/v1/inventory/spools`.

## Decision

FoxForge uses a server-owned bounded application event journal and SSE.

```text
Bambu / Moonraker transports
          |
PrinterAdapter normalized events
          |
      FleetService
          |                         SQLite queue/inventory writes
          |                                  |
          +------------+---------------------+
                       |
              ApplicationEventJournal
               epoch + sequence
                       |
                GET /api/v1/events
                       |
              browser EventSource
                       |
          TanStack Query invalidation
                       |
       canonical HTTP snapshot refresh
```

SSE is preferred for P2 because delivery is one-way server → browser, native browsers already implement reconnect and `Last-Event-ID`, and FoxForge does not need to create another bidirectional protocol beside its guarded HTTP command API.

## Stream identity and replay

Each running FoxForge process owns one random `streamEpoch` and a monotonically increasing `sequence`.

Every SSE item has an id:

```text
<streamEpoch>:<sequence>
```

The journal keeps a bounded in-memory replay window. The browser reconnects through the standard `Last-Event-ID` mechanism.

A cursor is replayable only when:

- its epoch matches the current process;
- its sequence is not in the future;
- every event after that sequence is still retained in the bounded replay window.

If those conditions hold, FoxForge replays the retained changes in sequence order and then emits `ready` at the current cursor.

## Resynchronization

FoxForge emits `resync_required` instead of guessing whenever continuity cannot be proven. This occurs for:

- a fresh browser connection without a cursor;
- a cursor from a previous server process/restart;
- a malformed cursor;
- a future sequence;
- a replay gap older than the retained journal;
- a subscriber that falls behind its bounded delivery queue.

The browser responds by invalidating all canonical snapshot query families. It never reconstructs missing state from partial realtime history.

This makes restart semantics explicit: the journal itself is intentionally in-memory. Durable state belongs to queue/inventory/configuration stores and is recovered through their normal HTTP read models after `resync_required`.

## Event types

P2 exposes three SSE event names:

| SSE event | Meaning |
| --- | --- |
| `change` | One application area changed and its canonical snapshot may be stale. |
| `ready` | Requested replay completed and the subscriber is caught up to the current cursor. |
| `resync_required` | Stream continuity cannot be proven; canonical snapshots must be refreshed. |

`change` payloads use FoxForge application topics:

| Topic | Source | Browser effect |
| --- | --- | --- |
| `fleet` | normalized `PrinterEvent` relay | invalidate fleet snapshots |
| `queue` | successful durable queue create/save | invalidate queue snapshots |
| `inventory` | successful durable inventory mutation | invalidate inventory snapshots |
| `printer_configuration` | successful add/update/remove | invalidate fleet snapshots |

The payload intentionally contains only `apiVersion`, stream cursor fields, application topic/change and an opaque FoxForge resource id where useful. Raw MQTT JSON, Moonraker JSON-RPC/WebSocket frames, secrets and vendor transport objects are prohibited.

## Durable-write ordering

Queue and inventory notifications are produced by store decorators:

```text
application mutation
      |
inner durable store write
      |
write succeeds
      |
publish application change
```

A failed durable write does not advance the realtime journal. This prevents another browser from being told to observe state that was never committed.

Printer configuration events are published only after the persisted configuration and live fleet mutation succeed. Connectivity-test operations do not emit configuration changes because they do not mutate durable configuration.

## Fleet event ordering

At runtime:

1. queue lifecycle tracking subscribes to normalized fleet events;
2. the P2 application relay subscribes and signals readiness;
3. only then does the printer reconnect supervisor start.

This prevents startup connection events from racing ahead of the application event relay.

Queue lifecycle updates may be triggered by the same normalized printer observation. When the durable queue entry changes, the eventing queue store emits a separate `queue` event after persistence. Clients therefore never rely on a fleet event alone to infer queue state.

## Browser behavior

The React application mounts one `EventSource('/api/v1/events')` bridge outside route-specific UI.

For `change` events it invalidates only the relevant TanStack Query family. Repeated changes are coalesced into a short 250 ms invalidation batch so frequent print-progress events do not create an HTTP refetch storm.

For `resync_required`, batching is bypassed and fleet, queue and inventory snapshot families are invalidated immediately.

Malformed or unknown event payloads fail closed to the same full snapshot resync.

The existing periodic polling remains a fallback during the P2 alpha stage. Realtime improves freshness but is not allowed to make the UI less recoverable if a reverse proxy or browser blocks/interrupts SSE.

## Heartbeats and proxies

The server emits an SSE comment heartbeat every 15 seconds while idle and sets:

- `Cache-Control: no-cache, no-transform`;
- `X-Accel-Buffering: no`;
- `Connection: keep-alive`.

The unified-container smoke test opens `/api/v1/events` and requires the initial `resync_required` contract, so Docker packaging validates that the streaming route is actually reachable in the built application.

## Security boundary

`/api/v1/events` is a read endpoint and follows the same exposure model as current public fleet/queue/inventory read models. It does not authorize mutations and carries no command credentials or secrets.

All state-changing operations continue to use ADR 0004 authenticated command routes. P2 does not create a command channel over SSE.

If future deployments require read-level authorization, it should be designed consistently for both snapshot reads and realtime delivery rather than adding a one-off event token.

## Acceptance criteria

P2 is complete when:

1. realtime delivery is FoxForge-owned and application-level; no vendor transport payload crosses the API/frontend boundary;
2. SSE supports `Last-Event-ID` replay through epoch + monotonic sequence cursors;
3. fresh/restarted/expired/malformed/overflowed streams produce `resync_required` rather than guessed continuity;
4. queue and inventory events occur only after successful durable writes, and failed writes emit no event;
5. printer add/update/remove and normalized fleet changes propagate to other browser clients;
6. runtime startup guarantees the application relay is subscribed before reconnect supervision;
7. the React bridge invalidates the correct TanStack Query families and fails closed to full resync for unknown data;
8. high-frequency changes are coalesced to avoid request storms;
9. periodic polling remains as an alpha fallback rather than being removed prematurely;
10. backend Ruff/tests pass on Python 3.12/3.13, frontend typecheck/tests/build pass, and the unified-container smoke validates the SSE endpoint;
11. README, project status, changelog and documentation index distinguish released `alpha.3` from post-alpha.3 P1/P2 source state.

## Deferred work

P2 does not introduce:

- durable event history across server restarts;
- multi-process/distributed event fan-out;
- browser-to-server commands over WebSocket/SSE;
- vendor protocol passthrough;
- removal of HTTP snapshots as the canonical state source;
- removal of fallback polling before representative Docker/Umbrel/browser validation.

A future multi-process FoxForge deployment would need a shared event bus or durable log and a new ADR before the current in-memory journal could be distributed safely.
