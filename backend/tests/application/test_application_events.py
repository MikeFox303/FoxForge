# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from foxforge.application.event_stores import EventingInventoryStore, EventingQueueStore
from foxforge.application.events import (
    ApplicationEventJournal,
    ApplicationEventTopic,
    ApplicationStreamItemKind,
)
from foxforge.application.inventory import InMemoryInventoryStore
from foxforge.application.queue import InMemoryQueueStore, QueueEntry, QueueEntryState
from foxforge.domain.inventory import Spool
from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat, PrintExecutionRequest


def test_fresh_subscription_requires_snapshot_resync() -> None:
    async def scenario() -> None:
        journal = ApplicationEventJournal()
        stream = journal.subscribe()
        try:
            item = await anext(stream)
            assert item.kind == ApplicationStreamItemKind.RESYNC_REQUIRED
            assert item.sequence == 0
            assert item.event_id == journal.cursor
        finally:
            await stream.aclose()  # type: ignore[attr-defined]

    asyncio.run(scenario())


def test_reconnect_replays_retained_changes_in_order_then_ready() -> None:
    async def scenario() -> None:
        journal = ApplicationEventJournal()
        first = journal.publish(ApplicationEventTopic.FLEET, "connection_changed", resource_id="printer-1")
        second = journal.publish(ApplicationEventTopic.QUEUE, "entry_changed", resource_id="queue-1")

        stream = journal.subscribe(first.event_id)
        try:
            replay = await anext(stream)
            ready = await anext(stream)
            assert replay == second
            assert ready.kind == ApplicationStreamItemKind.READY
            assert ready.sequence == second.sequence
            assert ready.event_id == journal.cursor
        finally:
            await stream.aclose()  # type: ignore[attr-defined]

    asyncio.run(scenario())


def test_unknown_or_expired_cursor_requires_resync() -> None:
    async def scenario() -> None:
        journal = ApplicationEventJournal(replay_capacity=2)
        journal.publish(ApplicationEventTopic.FLEET, "one")
        journal.publish(ApplicationEventTopic.FLEET, "two")
        journal.publish(ApplicationEventTopic.FLEET, "three")

        expired = journal.subscribe(f"{journal.stream_epoch}:0")
        foreign = journal.subscribe(f"{uuid4()}:3")
        try:
            assert (await anext(expired)).kind == ApplicationStreamItemKind.RESYNC_REQUIRED
            assert (await anext(foreign)).kind == ApplicationStreamItemKind.RESYNC_REQUIRED
        finally:
            await expired.aclose()  # type: ignore[attr-defined]
            await foreign.aclose()  # type: ignore[attr-defined]

    asyncio.run(scenario())


def test_slow_subscriber_is_failed_closed_to_resync() -> None:
    async def scenario() -> None:
        journal = ApplicationEventJournal(subscriber_capacity=1)
        stream = journal.subscribe()
        journal.publish(ApplicationEventTopic.FLEET, "one")
        journal.publish(ApplicationEventTopic.FLEET, "two")
        try:
            item = await anext(stream)
            assert item.kind == ApplicationStreamItemKind.RESYNC_REQUIRED
            assert item.sequence == journal.sequence
        finally:
            await stream.aclose()  # type: ignore[attr-defined]

    asyncio.run(scenario())


def test_eventing_queue_store_publishes_only_after_successful_durable_write() -> None:
    async def scenario() -> None:
        journal = ApplicationEventJournal()
        store = EventingQueueStore(InMemoryQueueStore(), journal)
        stream = journal.subscribe()
        await anext(stream)

        now = datetime.now(UTC)
        entry = QueueEntry(
            queue_id=uuid4(),
            printer_id="printer-1",
            request=PrintExecutionRequest(
                dispatch_id=uuid4(),
                artifact=LocalPrintArtifact(
                    artifact_id="artifact-1",
                    path=Path("/data/artifacts/test.gcode"),
                    filename="test.gcode",
                    format=PrintArtifactFormat.GCODE,
                    sha256="a" * 64,
                    size_bytes=10,
                ),
            ),
            state=QueueEntryState.PENDING,
            created_at=now,
            updated_at=now,
        )
        store.create(entry)
        try:
            event = await anext(stream)
            assert event.topic == ApplicationEventTopic.QUEUE
            assert event.change == "entry_changed"
            assert event.resource_id == str(entry.queue_id)
        finally:
            await stream.aclose()  # type: ignore[attr-defined]

    asyncio.run(scenario())


def test_eventing_inventory_store_publishes_mutation_after_store_commit() -> None:
    async def scenario() -> None:
        journal = ApplicationEventJournal()
        store = EventingInventoryStore(InMemoryInventoryStore(), journal)
        stream = journal.subscribe()
        await anext(stream)

        now = datetime.now(UTC)
        spool = Spool(
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
        store.create_spool(spool)
        try:
            event = await anext(stream)
            assert event.topic == ApplicationEventTopic.INVENTORY
            assert event.change == "spool_changed"
            assert event.resource_id == str(spool.spool_id)
        finally:
            await stream.aclose()  # type: ignore[attr-defined]

    asyncio.run(scenario())