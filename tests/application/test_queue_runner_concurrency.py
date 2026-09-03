# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

from foxforge.application.fleet import FleetService
from foxforge.application.queue import InMemoryQueueStore, QueueRunner, QueueService
from tests.helpers import make_artifact


def test_runner_serializes_concurrent_run_once_calls(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        queue = QueueService(FleetService([]), InMemoryQueueStore())
        runner = QueueRunner(queue)
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))

        active_dispatches = 0
        max_active_dispatches = 0

        async def slow_dispatch(queue_id):
            nonlocal active_dispatches, max_active_dispatches
            active_dispatches += 1
            max_active_dispatches = max(max_active_dispatches, active_dispatches)
            try:
                await asyncio.sleep(0.02)
                return queue.get(queue_id)
            finally:
                active_dispatches -= 1

        queue.dispatch = slow_dispatch  # type: ignore[method-assign]

        first, second = await asyncio.gather(runner.run_once(), runner.run_once())
        assert first[0].queue_id == entry.queue_id
        assert second[0].queue_id == entry.queue_id
        assert max_active_dispatches == 1

        await queue.aclose()

    asyncio.run(scenario())
