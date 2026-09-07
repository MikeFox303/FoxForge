# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

import pytest

from foxforge.application.fleet import FleetService
from foxforge.application.queue import InMemoryQueueStore, QueueEntryState, QueueService
from foxforge.domain.printers import ActiveJobSnapshot, JobState, OperationalState
from foxforge.testing import build_fake_printer
from tests.helpers import make_artifact


async def _wait_for_state(queue: QueueService, queue_id, state: QueueEntryState) -> None:
    for _ in range(100):
        if queue.get(queue_id).state == state:
            return
        await asyncio.sleep(0.005)
    assert queue.get(queue_id).state == state


def _job(vendor_job_id: str, state: JobState) -> ActiveJobSnapshot:
    return ActiveJobSnapshot(
        vendor_job_id=vendor_job_id,
        name="job.gcode",
        state=state,
        progress=None,
        elapsed_seconds=None,
        remaining_seconds=None,
        current_layer=None,
        total_layers=None,
    )


@pytest.mark.parametrize(
    ("job_state", "queue_state", "operational_state"),
    [
        (JobState.FAILED, QueueEntryState.FAILED, OperationalState.FAILED),
        (JobState.CANCELLED, QueueEntryState.CANCELLED, OperationalState.CANCELLING),
    ],
)
def test_confirmed_terminal_failure_or_cancel_cannot_regress(
    tmp_path,
    printer_identity,
    job_state: JobState,
    queue_state: QueueEntryState,
    operational_state: OperationalState,
) -> None:
    async def scenario() -> None:
        adapter, _, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        queue = QueueService(FleetService([adapter]), InMemoryQueueStore())
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))
        accepted = await queue.dispatch(entry.queue_id)
        assert accepted.receipt is not None
        vendor_job_id = accepted.receipt.vendor_job_id
        assert vendor_job_id is not None

        adapter.set_active_job(_job(vendor_job_id, job_state), operational_state=operational_state)
        await _wait_for_state(queue, entry.queue_id, queue_state)
        terminal = queue.get(entry.queue_id)
        assert terminal.receipt == accepted.receipt
        assert terminal.terminal is True

        adapter.set_active_job(
            _job(vendor_job_id, JobState.PRINTING),
            operational_state=OperationalState.PRINTING,
        )
        await asyncio.sleep(0.02)
        assert queue.get(entry.queue_id).state == queue_state
        await queue.aclose()

    asyncio.run(scenario())


def test_queue_event_subscription_can_close_idempotently_and_restart(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, _, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        queue = QueueService(FleetService([adapter]), InMemoryQueueStore())
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))
        accepted = await queue.dispatch(entry.queue_id)
        assert accepted.receipt is not None
        vendor_job_id = accepted.receipt.vendor_job_id
        assert vendor_job_id is not None

        await queue.aclose()
        await queue.aclose()
        await queue.start()

        adapter.set_active_job(
            _job(vendor_job_id, JobState.PRINTING),
            operational_state=OperationalState.PRINTING,
        )
        await _wait_for_state(queue, entry.queue_id, QueueEntryState.PRINTING)
        await queue.aclose()

    asyncio.run(scenario())
