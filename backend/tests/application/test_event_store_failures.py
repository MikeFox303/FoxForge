# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from foxforge.application.event_stores import EventingInventoryStore, EventingQueueStore
from foxforge.application.events import ApplicationEventJournal
from foxforge.application.inventory import InMemoryInventoryStore
from foxforge.application.inventory.store import InventoryStoreConflictError
from foxforge.application.queue import InMemoryQueueStore, QueueEntry, QueueEntryState
from foxforge.application.queue.store import QueueStoreConflictError
from foxforge.domain.inventory import Spool
from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat, PrintExecutionRequest


def _queue_entry() -> QueueEntry:
    now = datetime.now(UTC)
    return QueueEntry(
        queue_id=uuid4(),
        printer_id="printer-1",
        request=PrintExecutionRequest(
            dispatch_id=uuid4(),
            artifact=LocalPrintArtifact(
                artifact_id="artifact-1",
                path=Path("/data/artifacts/test.gcode"),
                filename="test.gcode",
                format=PrintArtifactFormat.GCODE,
                size_bytes=10,
                sha256="a" * 64,
            ),
        ),
        state=QueueEntryState.PENDING,
        created_at=now,
        updated_at=now,
    )


def _spool() -> Spool:
    now = datetime.now(UTC)
    return Spool(
        spool_id=uuid4(),
        material_family="PLA",
        initial_filament_mass_g=Decimal("1000"),
        manufacturer=None,
        product_name=None,
        color=None,
        empty_spool_mass_g=None,
        purchase_date=None,
        created_at=now,
        updated_at=now,
    )


def test_failed_queue_write_does_not_advance_realtime_journal() -> None:
    journal = ApplicationEventJournal()
    store = EventingQueueStore(InMemoryQueueStore(), journal)
    entry = _queue_entry()

    store.create(entry)
    assert journal.sequence == 1

    with pytest.raises(QueueStoreConflictError):
        store.create(entry)

    assert journal.sequence == 1


def test_failed_inventory_write_does_not_advance_realtime_journal() -> None:
    journal = ApplicationEventJournal()
    store = EventingInventoryStore(InMemoryInventoryStore(), journal)
    spool = _spool()

    store.create_spool(spool)
    assert journal.sequence == 1

    with pytest.raises(InventoryStoreConflictError):
        store.create_spool(spool)

    assert journal.sequence == 1
