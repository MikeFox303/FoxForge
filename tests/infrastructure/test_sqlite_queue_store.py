# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

import pytest

from foxforge.application.fleet import FleetService
from foxforge.application.queue import QueueEntryState, QueueReconciliationRequiredError, QueueService
from foxforge.infrastructure.queue import SQLiteQueueStore
from foxforge.testing import build_fake_printer
from tests.helpers import make_artifact


def test_accepted_dispatch_survives_store_and_adapter_restart(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        database = tmp_path / "queue.db"
        artifact = make_artifact(tmp_path / "job.gcode")

        first_adapter, first_printing, _ = build_fake_printer(
            printer_identity,
            supports_material_bindings=False,
        )
        await first_adapter.connect()
        first_queue = QueueService(FleetService([first_adapter]), SQLiteQueueStore(database))
        entry = first_queue.enqueue(printer_identity.printer_id, artifact)
        accepted = await first_queue.dispatch(entry.queue_id)
        assert accepted.state == QueueEntryState.ACCEPTED
        assert first_printing.start_count == 1

        second_adapter, second_printing, _ = build_fake_printer(
            printer_identity,
            supports_material_bindings=False,
        )
        await second_adapter.connect()
        second_queue = QueueService(FleetService([second_adapter]), SQLiteQueueStore(database))
        restored = second_queue.get(entry.queue_id)
        assert restored == accepted

        repeated = await second_queue.dispatch(entry.queue_id)
        assert repeated == accepted
        assert second_printing.start_count == 0

    asyncio.run(scenario())


def test_indeterminate_dispatch_survives_restart_and_blocks_retry(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        database = tmp_path / "queue.db"
        artifact = make_artifact(tmp_path / "job.gcode")

        first_adapter, first_printing, _ = build_fake_printer(
            printer_identity,
            supports_material_bindings=False,
        )
        first_printing.make_next_submit_indeterminate()
        await first_adapter.connect()
        first_queue = QueueService(FleetService([first_adapter]), SQLiteQueueStore(database))
        entry = first_queue.enqueue(printer_identity.printer_id, artifact)
        uncertain = await first_queue.dispatch(entry.queue_id)
        assert uncertain.state == QueueEntryState.INDETERMINATE

        second_adapter, second_printing, _ = build_fake_printer(
            printer_identity,
            supports_material_bindings=False,
        )
        await second_adapter.connect()
        second_queue = QueueService(FleetService([second_adapter]), SQLiteQueueStore(database))

        with pytest.raises(QueueReconciliationRequiredError):
            await second_queue.dispatch(entry.queue_id)
        assert second_printing.start_count == 0

    asyncio.run(scenario())


def test_sqlite_store_preserves_queue_order_and_request_identity(tmp_path, printer_identity) -> None:
    database = tmp_path / "queue.db"
    store = SQLiteQueueStore(database)
    queue = QueueService(FleetService([]), store)
    first = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "one.gcode"))
    second = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "two.gcode"))

    restored = SQLiteQueueStore(database).list()
    assert [entry.queue_id for entry in restored] == [first.queue_id, second.queue_id]
    assert restored[0].request.dispatch_id == first.request.dispatch_id
    assert restored[1].request.dispatch_id == second.request.dispatch_id
