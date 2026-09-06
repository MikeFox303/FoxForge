# Realtime application events

- **Status:** implemented and released
- **Updated:** 2026-09-06
- **Related:** [public API v1](public-api-v1.md), [web UI](web-ui-foundation.md)

## Purpose

FoxForge uses application-owned realtime events to reduce browser polling latency without turning printer transport events into a public wire contract or creating a second canonical state store.

> **Realtime events are invalidations; canonical state remains the HTTP read model.**

## Source boundary

Application/runtime events are published only after the relevant durable mutation succeeds. Printer/fleet events are normalized before they enter this layer.

The public SSE stream therefore carries FoxForge topic/resource/revision information, not raw MQTT or Moonraker payloads.

## Delivery model

`/api/v1/events` provides Server-Sent Events with bounded replay/resync semantics.

Clients use event IDs/revision continuity where available. When continuity cannot be guaranteed—buffer gap, malformed/unknown event, reconnect requiring resync—the server/client signals/handles `resync_required` and the browser refetches canonical HTTP state.

The stream may batch/coalesce frequent invalidations; it must not drop the need to refresh terminal/durable state.

## Current topic families

Representative application topics include fleet/printer configuration/state, queue and inventory changes. Topic names are FoxForge contracts and may evolve compatibly within the v1 application event model.

## Frontend behavior

The React realtime bridge maps events to TanStack Query invalidation. It does not mutate queue/inventory/fleet state directly from event payloads.

Polling remains an alpha fallback/recovery mechanism and is not evidence that SSE is authoritative.

## Safety

- queue/inventory events publish after persistence;
- replay/resync cannot invoke a printer command;
- browser refetch after `INDETERMINATE` observes state but does not resend side effects;
- reconnect storms are bounded/coalesced;
- one slow/old browser cannot stall the application event publisher.

## Deployment

The unified Python runtime serves both SPA/API and SSE. Docker and Umbrel therefore use the same application-event semantics; physical reverse-proxy/reconnect behavior still requires representative deployment validation.

## Acceptance criteria

- API exposes only FoxForge event DTOs;
- HTTP snapshots remain canonical;
- persistence precedes durable queue/inventory invalidation;
- replay gap forces resync rather than invented continuity;
- frontend invalidates/refetchs TanStack Query caches;
- realtime processing never automatically repeats physical side effects;
- representative production-container browser acceptance remains green.
