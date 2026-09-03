# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from foxforge.application.fleet import FleetService
from foxforge.application.queue import (
    InMemoryQueueStore,
    QueueEntryState,
    QueueReconciliationRequiredError,
    QueueService,
)
from foxforge.domain.printers import PrinterErrorCode, utc_now
from foxforge.domain.printers.capabilities import PrintAssessmentBlockerCode
from foxforge.testing import FakePrinterAdapter, build_fake_printer
from tests.helpers import make_artifact


def test_enqueue_persists_dispatch_id_before_submit(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        store = InMemoryQueueStore()
        queue = QueueService(FleetService([adapter]), store)
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))

        persisted = store.get(entry.queue_id)
        assert persisted is not None
        assert persisted.request.dispatch_id == entry.request.dispatch_id
        assert persisted.state == QueueEntryState.PENDING
        assert printing.start_count == 0

        accepted = await queue.dispatch(entry.queue_id)
        assert accepted.state == QueueEntryState.ACCEPTED
        assert accepted.receipt is not None
        assert printing.start_count == 1

    asyncio.run(scenario())


def test_accepted_dispatch_is_durably_idempotent_at_queue_layer(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        store = InMemoryQueueStore()
        queue = QueueService(FleetService([adapter]), store)
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))

        first = await queue.dispatch(entry.queue_id)
        second = await queue.dispatch(entry.queue_id)

        assert second == first
        assert second.state == QueueEntryState.ACCEPTED
        assert printing.start_count == 1
        assert second.attempt_count == 1

    asyncio.run(scenario())


def test_indeterminate_dispatch_cannot_be_blindly_retried(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        printing.make_next_submit_indeterminate()
        await adapter.connect()
        store = InMemoryQueueStore()
        queue = QueueService(FleetService([adapter]), store)
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))

        uncertain = await queue.dispatch(entry.queue_id)
        assert uncertain.state == QueueEntryState.INDETERMINATE
        assert uncertain.error is not None
        assert uncertain.error.code == PrinterErrorCode.INDETERMINATE
        assert printing.start_count == 1

        with pytest.raises(QueueReconciliationRequiredError):
            await queue.dispatch(entry.queue_id)
        assert printing.start_count == 1

    asyncio.run(scenario())


def test_persisted_dispatching_state_requires_reconciliation_after_restart(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        store = InMemoryQueueStore()
        first_process = QueueService(FleetService([adapter]), store)
        entry = first_process.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))

        crash_boundary = replace(
            entry,
            state=QueueEntryState.DISPATCHING,
            attempt_count=1,
            last_attempt_at=utc_now(),
            updated_at=utc_now(),
        )
        store.save(crash_boundary)

        second_process = QueueService(FleetService([adapter]), store)
        with pytest.raises(QueueReconciliationRequiredError):
            await second_process.dispatch(entry.queue_id)
        assert printing.start_count == 0

    asyncio.run(scenario())


def test_negative_reconciliation_allows_explicit_retry_with_same_dispatch_id(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        printing.make_next_submit_indeterminate()
        await adapter.connect()
        store = InMemoryQueueStore()
        queue = QueueService(FleetService([adapter]), store)
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))

        uncertain = await queue.dispatch(entry.queue_id)
        assert uncertain.state == QueueEntryState.INDETERMINATE
        dispatch_id = uncertain.request.dispatch_id

        assert printing.resolve_indeterminate(dispatch_id, accepted=False) is None
        pending = queue.resolve_reconciliation(entry.queue_id, accepted=False)
        assert pending.state == QueueEntryState.PENDING
        assert pending.request.dispatch_id == dispatch_id

        accepted = await queue.dispatch(entry.queue_id)
        assert accepted.state == QueueEntryState.ACCEPTED
        assert accepted.request.dispatch_id == dispatch_id
        assert accepted.attempt_count == 2

    asyncio.run(scenario())


def test_positive_reconciliation_creates_receipt_without_second_submit(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        printing.make_next_submit_indeterminate()
        await adapter.connect()
        store = InMemoryQueueStore()
        queue = QueueService(FleetService([adapter]), store)
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))

        uncertain = await queue.dispatch(entry.queue_id)
        assert uncertain.state == QueueEntryState.INDETERMINATE
        resolved = queue.resolve_reconciliation(entry.queue_id, accepted=True, vendor_job_id="reconciled-job")
        assert resolved.state == QueueEntryState.ACCEPTED
        assert resolved.receipt is not None
        assert resolved.receipt.vendor_job_id == "reconciled-job"

        again = await queue.dispatch(entry.queue_id)
        assert again == resolved
        assert printing.start_count == 1

    asyncio.run(scenario())


def test_printer_without_print_execution_is_blocked_not_vendor_special_cased(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter = FakePrinterAdapter(printer_identity)
        await adapter.connect()
        queue = QueueService(FleetService([adapter]), InMemoryQueueStore())
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "job.gcode"))

        blocked = await queue.dispatch(entry.queue_id)
        assert blocked.state == QueueEntryState.BLOCKED
        assert blocked.assessment is not None
        assert blocked.assessment.blockers[0].code == PrintAssessmentBlockerCode.UNKNOWN

    asyncio.run(scenario())
