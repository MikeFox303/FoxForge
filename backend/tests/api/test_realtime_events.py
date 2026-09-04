# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

import asyncio
import json

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1.realtime import register_realtime_routes
from foxforge.application.events import ApplicationEventJournal, ApplicationEventTopic


async def _read_event(response) -> tuple[str, str, dict[str, object]]:
    event_id = (await response.content.readline()).decode().removeprefix("id: ").strip()
    event_type = (await response.content.readline()).decode().removeprefix("event: ").strip()
    data_line = (await response.content.readline()).decode().removeprefix("data: ").strip()
    assert await response.content.readline() == b"\n"
    return event_id, event_type, json.loads(data_line)


def test_fresh_sse_connection_requires_snapshot_resync() -> None:
    async def scenario() -> None:
        journal = ApplicationEventJournal()
        app = web.Application()
        register_realtime_routes(app, journal=journal)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/api/v1/events")
            assert response.status == 200
            assert response.headers["Content-Type"].startswith("text/event-stream")
            assert response.headers["Cache-Control"] == "no-cache, no-transform"

            event_id, event_type, payload = await _read_event(response)
            assert event_type == "resync_required"
            assert event_id == journal.cursor
            assert payload["apiVersion"] == "1"
            assert payload["sequence"] == 0
            response.close()
        finally:
            await client.close()

    asyncio.run(scenario())


def test_sse_last_event_id_replays_retained_changes_before_ready() -> None:
    async def scenario() -> None:
        journal = ApplicationEventJournal()
        first = journal.publish(ApplicationEventTopic.FLEET, "connection_changed", resource_id="printer-1")
        second = journal.publish(ApplicationEventTopic.QUEUE, "entry_changed", resource_id="queue-1")

        app = web.Application()
        register_realtime_routes(app, journal=journal)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/api/v1/events", headers={"Last-Event-ID": first.event_id})
            replay_id, replay_type, replay_payload = await _read_event(response)
            ready_id, ready_type, ready_payload = await _read_event(response)

            assert replay_type == "change"
            assert replay_id == second.event_id
            assert replay_payload["topic"] == "queue"
            assert replay_payload["resourceId"] == "queue-1"
            assert ready_type == "ready"
            assert ready_id == journal.cursor
            assert ready_payload["sequence"] == second.sequence
            response.close()
        finally:
            await client.close()

    asyncio.run(scenario())
