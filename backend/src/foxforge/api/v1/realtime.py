# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from aiohttp import web

from foxforge.application.events import ApplicationEventJournal, ApplicationStreamItem

_HEARTBEAT_SECONDS = 15.0


def register_realtime_routes(app: web.Application, *, journal: ApplicationEventJournal) -> None:
    """Expose FoxForge-owned application events over Server-Sent Events."""

    async def application_events(request: web.Request) -> web.StreamResponse:
        stream = journal.subscribe(request.headers.get("Last-Event-ID"))
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream; charset=utf-8",
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        await response.prepare(request)
        try:
            while True:
                try:
                    item = await asyncio.wait_for(anext(stream), timeout=_HEARTBEAT_SECONDS)
                except TimeoutError:
                    await response.write(b": foxforge heartbeat\n\n")
                    continue
                await response.write(_encode_sse(item))
        except (ConnectionResetError, BrokenPipeError):
            return response
        except asyncio.CancelledError:
            raise
        finally:
            await _close_stream(stream)

    app.router.add_get("/api/v1/events", application_events)


def _encode_sse(item: ApplicationStreamItem) -> bytes:
    payload: dict[str, object] = {
        "apiVersion": "1",
        "streamEpoch": str(item.stream_epoch),
        "sequence": item.sequence,
        "emittedAt": item.emitted_at.isoformat().replace("+00:00", "Z"),
    }
    if item.topic is not None:
        payload["topic"] = item.topic.value
    if item.change is not None:
        payload["change"] = item.change
    if item.resource_id is not None:
        payload["resourceId"] = item.resource_id

    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return f"id: {item.event_id}\nevent: {item.kind.value}\ndata: {data}\n\n".encode()


async def _close_stream(stream: AsyncIterator[ApplicationStreamItem]) -> None:
    close = getattr(stream, "aclose", None)
    if close is not None:
        await close()
