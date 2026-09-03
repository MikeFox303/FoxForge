# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta

import pytest

from foxforge.application.fleet import FleetService
from foxforge.application.queue import (
    InMemoryQueueStore,
    QueueEntryState,
    QueueRetryPolicy,
    QueueRunner,
    QueueService,
)
from foxforge.domain.printers import (
    ActiveJobSnapshot,
    JobState,
    OperationalState,
    PrinterAdapterError,
    PrinterErrorCode,
)
from foxforge.testing import build_fake_printer
from tests.helpers import make_artifact


def test_retry_policy_backoff_and_cap() -> None:
    policy = QueueRetryPolicy(
        initial_delay_seconds=5,
        backoff_multiplier=2,
        max_delay_seconds=12,
        max_attempts=5,
    )

    assert policy.delay_after_attempt(1) == timedelta(seconds=5)
    assert policy.delay_after_attempt(2) == timedelta(seconds=10)
    assert policy.delay_after_attempt(3) == timedelta(seconds=12)
    assert policy.delay_after_attempt(10) == timedelta(seconds=12)

    with pytest.raises(ValueError, match="attempt_count"):
        policy.delay_after_attempt(0)


def test_runner_retries_only_after_backoff_with_same_dispatch_id(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        printing.fail_next_submit(
            PrinterAdapterError(
                PrinterErrorCode.CONNECTION_UNAVAILABLE,
                "known pre-start connection failure",
                retryable=True,
            )
        )
        store = InMemoryQueueStore()
        queue = QueueService(FleetService([adapter]), store)
        runner = QueueRunner(
            queue,
            retry_policy=QueueRetryPolicy(
                initial_delay_seconds=30,
                backoff_multiplier=2,
                max_delay_seconds=120,
                max_attempts=3,
            ),
        )
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))
        failed = await queue.dispatch(entry.queue_id)

        assert failed.state == QueueEntryState.FAILED
        assert failed.error is not None and failed.error.retryable is True
        assert failed.attempt_count == 1
        assert failed.last_attempt_at is not None
        dispatch_id = failed.request.dispatch_id

        too_early = await runner.run_once(now=failed.last_attempt_at + timedelta(seconds=29))
        assert too_early == ()
        assert printing.submit_attempt_count == 1

        retried = await runner.run_once(now=failed.last_attempt_at + timedelta(seconds=30))
        assert len(retried) == 1
        accepted = retried[0]
        assert accepted.state == QueueEntryState.ACCEPTED
        assert accepted.request.dispatch_id == dispatch_id
        assert accepted.attempt_count == 2
        assert printing.submit_attempt_count == 2
        assert printing.start_count == 1

        await queue.aclose()

    asyncio.run(scenario())


def test_runner_never_retries_indeterminate_dispatch(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        printing.make_next_submit_indeterminate()
        await adapter.connect()
        queue = QueueService(FleetService([adapter]), InMemoryQueueStore())
        runner = QueueRunner(queue, retry_policy=QueueRetryPolicy(initial_delay_seconds=0))
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))
        uncertain = await queue.dispatch(entry.queue_id)

        assert uncertain.state == QueueEntryState.INDETERMINATE
        assert uncertain.last_attempt_at is not None
        assert printing.start_count == 1

        processed = await runner.run_once(now=uncertain.last_attempt_at + timedelta(days=1))
        assert processed == ()
        assert printing.submit_attempt_count == 1
        assert printing.start_count == 1
        assert queue.get(entry.queue_id).state == QueueEntryState.INDETERMINATE

        await queue.aclose()

    asyncio.run(scenario())


def test_runner_skips_nonretryable_and_exhausted_failures(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        store = InMemoryQueueStore()
        queue = QueueService(FleetService([adapter]), store)
        runner = QueueRunner(
            queue,
            retry_policy=QueueRetryPolicy(initial_delay_seconds=0, max_attempts=2),
        )

        printing.fail_next_submit(
            PrinterAdapterError(
                PrinterErrorCode.INVALID_REQUEST,
                "invalid request",
                retryable=False,
            )
        )
        nonretryable_entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "invalid.gcode"),
        )
        nonretryable = await queue.dispatch(nonretryable_entry.queue_id)
        assert nonretryable.state == QueueEntryState.FAILED
        assert nonretryable.error is not None and nonretryable.error.retryable is False

        assert await runner.run_once() == ()
        assert printing.submit_attempt_count == 1

        retryable_entry = queue.enqueue(
            printer_identity.printer_id,
            make_artifact(tmp_path / "exhausted.gcode"),
        )
        exhausted = replace(
            retryable_entry,
            state=QueueEntryState.FAILED,
            error=replace(nonretryable.error, retryable=True),
            attempt_count=2,
            last_attempt_at=retryable_entry.updated_at,
            updated_at=retryable_entry.updated_at,
        )
        store.save(exhausted)

        assert await runner.run_once() == ()
        assert queue.get(retryable_entry.queue_id).state == QueueEntryState.FAILED
        assert printing.submit_attempt_count == 1

        await queue.aclose()

    asyncio.run(scenario())


def test_runner_reassesses_blocked_entry_without_counting_dispatch_attempt(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        adapter.set_operational_state(OperationalState.PRINTING)
        queue = QueueService(FleetService([adapter]), InMemoryQueueStore())
        runner = QueueRunner(queue)
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))

        blocked = await queue.dispatch(entry.queue_id)
        assert blocked.state == QueueEntryState.BLOCKED
        assert blocked.attempt_count == 0
        assert printing.submit_attempt_count == 0

        adapter.set_active_job(None, operational_state=OperationalState.IDLE)
        processed = await runner.run_once()
        assert len(processed) == 1
        assert processed[0].state == QueueEntryState.ACCEPTED
        assert processed[0].attempt_count == 1
        assert printing.start_count == 1

        await queue.aclose()

    asyncio.run(scenario())


def test_runner_processes_at_most_one_entry_per_printer_per_pass(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        queue = QueueService(FleetService([adapter]), InMemoryQueueStore())
        runner = QueueRunner(queue)
        first = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "one.gcode"))
        second = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "two.gcode"))

        processed = await runner.run_once()
        assert [entry.queue_id for entry in processed] == [first.queue_id]
        assert queue.get(first.queue_id).state == QueueEntryState.ACCEPTED
        assert queue.get(second.queue_id).state == QueueEntryState.PENDING
        assert printing.start_count == 1

        await queue.aclose()

    asyncio.run(scenario())


def test_runner_never_retries_remote_failed_receipt_bearing_job(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        queue = QueueService(FleetService([adapter]), InMemoryQueueStore())
        runner = QueueRunner(queue, retry_policy=QueueRetryPolicy(initial_delay_seconds=0))
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))
        accepted = await queue.dispatch(entry.queue_id)
        assert accepted.receipt is not None and accepted.receipt.vendor_job_id is not None

        adapter.set_active_job(
            ActiveJobSnapshot(
                vendor_job_id=accepted.receipt.vendor_job_id,
                name="job.gcode",
                state=JobState.FAILED,
                progress=0.5,
                elapsed_seconds=30,
                remaining_seconds=None,
                current_layer=None,
                total_layers=None,
            ),
            operational_state=OperationalState.FAILED,
        )
        for _ in range(100):
            if queue.get(entry.queue_id).state == QueueEntryState.FAILED:
                break
            await asyncio.sleep(0.005)

        remote_failed = queue.get(entry.queue_id)
        assert remote_failed.state == QueueEntryState.FAILED
        assert remote_failed.receipt == accepted.receipt

        processed = await runner.run_once()
        assert processed == ()
        assert printing.submit_attempt_count == 1
        assert printing.start_count == 1

        await queue.aclose()

    asyncio.run(scenario())
