# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

import pytest

from foxforge.application.fleet import FleetService
from foxforge.application.queue import QueueEntryState, QueueReconciliationRequiredError, QueueService
from foxforge.domain.printers import ActiveJobSnapshot, JobState, OperationalState
from foxforge.infrastructure.queue import SQLiteQueueStore
from foxforge.testing import build_fake_printer
from tests.helpers import make_artifact


async def _wait_for_state(queue: QueueService, queue_id, state: QueueEntryState) -> None:
    for _ in range(100):
        if queue.get(queue_id).state == state:
            return
        await asyncio.sleep(0.005)
    assert queue.get(queue_id).state == state


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


def test_completed_remote_lifecycle_and_receipt_survive_sqlite_restart(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        database = tmp_path / "queue.db"
        artifact = make_artifact(tmp_path / "job.gcode")
        adapter, _, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        queue = QueueService(FleetService([adapter]), SQLiteQueueStore(database))
        entry = queue.enqueue(printer_identity.printer_id, artifact)
        accepted = await queue.dispatch(entry.queue_id)
        assert accepted.receipt is not None
        vendor_job_id = accepted.receipt.vendor_job_id
        assert vendor_job_id is not None

        adapter.set_active_job(
            ActiveJobSnapshot(
                vendor_job_id=vendor_job_id,
                name="job.gcode",
                state=JobState.COMPLETED,
                progress=1.0,
                elapsed_seconds=60,
                remaining_seconds=0,
                current_layer=10,
                total_layers=10,
            ),
            operational_state=OperationalState.COMPLETED,
        )
        await _wait_for_state(queue, entry.queue_id, QueueEntryState.COMPLETED)
        completed = queue.get(entry.queue_id)
        assert completed.receipt == accepted.receipt
        await queue.aclose()

        restored = SQLiteQueueStore(database).get(entry.queue_id)
        assert restored == completed
        assert restored is not None
        assert restored.state == QueueEntryState.COMPLETED
        assert restored.receipt == accepted.receipt
        assert restored.terminal is True

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
