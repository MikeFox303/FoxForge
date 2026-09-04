# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from foxforge.domain.printers import PrinterEvent, utc_now


class ApplicationEventTopic(StrEnum):
    FLEET = "fleet"
    QUEUE = "queue"
    INVENTORY = "inventory"
    PRINTER_CONFIGURATION = "printer_configuration"


class ApplicationStreamItemKind(StrEnum):
    CHANGE = "change"
    READY = "ready"
    RESYNC_REQUIRED = "resync_required"


@dataclass(frozen=True, slots=True)
class ApplicationStreamItem:
    kind: ApplicationStreamItemKind
    stream_epoch: UUID
    sequence: int
    emitted_at: datetime
    topic: ApplicationEventTopic | None = None
    change: str | None = None
    resource_id: str | None = None

    @property
    def event_id(self) -> str:
        return f"{self.stream_epoch}:{self.sequence}"


class _ApplicationEventSubscription(AsyncIterator[ApplicationStreamItem]):
    def __init__(
        self,
        journal: ApplicationEventJournal,
        queue: asyncio.Queue[ApplicationStreamItem],
    ) -> None:
        self._journal = journal
        self._queue = queue
        self._closed = False

    def __aiter__(self) -> _ApplicationEventSubscription:
        return self

    async def __anext__(self) -> ApplicationStreamItem:
        if self._closed:
            raise StopAsyncIteration
        return await self._queue.get()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._journal._subscribers.discard(self._queue)


class ApplicationEventJournal:
    """Bounded application-level event journal for browser realtime delivery.

    The journal owns its own stream epoch and monotonically increasing sequence.
    It never exposes vendor transport payloads. Consumers that reconnect with a
    cursor outside the retained window receive RESYNC_REQUIRED and must refresh
    canonical HTTP snapshots instead of guessing missing state.
    """

    def __init__(self, *, replay_capacity: int = 512, subscriber_capacity: int = 128) -> None:
        if replay_capacity <= 0:
            raise ValueError("replay_capacity must be positive")
        if subscriber_capacity <= 0:
            raise ValueError("subscriber_capacity must be positive")
        self._stream_epoch = uuid4()
        self._sequence = 0
        self._replay: deque[ApplicationStreamItem] = deque(maxlen=replay_capacity)
        self._subscriber_capacity = subscriber_capacity
        self._subscribers: set[asyncio.Queue[ApplicationStreamItem]] = set()

    @property
    def stream_epoch(self) -> UUID:
        return self._stream_epoch

    @property
    def sequence(self) -> int:
        return self._sequence

    @property
    def cursor(self) -> str:
        return f"{self._stream_epoch}:{self._sequence}"

    def publish(
        self,
        topic: ApplicationEventTopic,
        change: str,
        *,
        resource_id: str | None = None,
    ) -> ApplicationStreamItem:
        normalized_change = change.strip()
        if not normalized_change:
            raise ValueError("change must not be empty")
        self._sequence += 1
        item = ApplicationStreamItem(
            kind=ApplicationStreamItemKind.CHANGE,
            stream_epoch=self._stream_epoch,
            sequence=self._sequence,
            emitted_at=utc_now(),
            topic=topic,
            change=normalized_change,
            resource_id=resource_id,
        )
        self._replay.append(item)
        for queue in tuple(self._subscribers):
            self._deliver(queue, item)
        return item

    def publish_printer_event(self, event: PrinterEvent) -> ApplicationStreamItem:
        return self.publish(
            ApplicationEventTopic.FLEET,
            event.kind.value,
            resource_id=event.printer_id,
        )

    def subscribe(self, last_event_id: str | None = None) -> AsyncIterator[ApplicationStreamItem]:
        asyncio.get_running_loop()
        queue: asyncio.Queue[ApplicationStreamItem] = asyncio.Queue(maxsize=self._subscriber_capacity)
        self._subscribers.add(queue)

        replay = self._replay_after(last_event_id)
        if replay is None:
            queue.put_nowait(self._control(ApplicationStreamItemKind.RESYNC_REQUIRED))
        else:
            for item in replay:
                self._deliver(queue, item)
            self._deliver(queue, self._control(ApplicationStreamItemKind.READY))
        return _ApplicationEventSubscription(self, queue)

    def _replay_after(self, last_event_id: str | None) -> tuple[ApplicationStreamItem, ...] | None:
        if last_event_id is None or not last_event_id.strip():
            return None
        try:
            epoch_text, sequence_text = last_event_id.strip().rsplit(":", 1)
            epoch = UUID(epoch_text)
            sequence = int(sequence_text)
        except (ValueError, TypeError):
            return None
        if epoch != self._stream_epoch or sequence < 0 or sequence > self._sequence:
            return None
        if not self._replay:
            return () if sequence == self._sequence else None

        oldest_sequence = self._replay[0].sequence
        if sequence < oldest_sequence - 1:
            return None
        return tuple(item for item in self._replay if item.sequence > sequence)

    def _control(self, kind: ApplicationStreamItemKind) -> ApplicationStreamItem:
        return ApplicationStreamItem(
            kind=kind,
            stream_epoch=self._stream_epoch,
            sequence=self._sequence,
            emitted_at=utc_now(),
        )

    def _deliver(self, queue: asyncio.Queue[ApplicationStreamItem], item: ApplicationStreamItem) -> None:
        try:
            queue.put_nowait(item)
            return
        except asyncio.QueueFull:
            pass

        while True:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        queue.put_nowait(self._control(ApplicationStreamItemKind.RESYNC_REQUIRED))
