# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from .models import QueueEntry


class QueueStoreConflictError(RuntimeError):
    def __init__(self, queue_id: UUID) -> None:
        self.queue_id = queue_id
        super().__init__(f"queue entry already exists: {queue_id}")


class QueueStoreMissingError(RuntimeError):
    def __init__(self, queue_id: UUID) -> None:
        self.queue_id = queue_id
        super().__init__(f"queue entry does not exist: {queue_id}")


class QueueStore(Protocol):
    def create(self, entry: QueueEntry) -> None: ...

    def save(self, entry: QueueEntry) -> None: ...

    def get(self, queue_id: UUID) -> QueueEntry | None: ...

    def list(self) -> tuple[QueueEntry, ...]: ...


class InMemoryQueueStore:
    """Deterministic non-durable store for tests and composition experiments."""

    def __init__(self) -> None:
        self._entries: dict[UUID, QueueEntry] = {}

    def create(self, entry: QueueEntry) -> None:
        if entry.queue_id in self._entries:
            raise QueueStoreConflictError(entry.queue_id)
        self._entries[entry.queue_id] = entry

    def save(self, entry: QueueEntry) -> None:
        if entry.queue_id not in self._entries:
            raise QueueStoreMissingError(entry.queue_id)
        self._entries[entry.queue_id] = entry

    def get(self, queue_id: UUID) -> QueueEntry | None:
        return self._entries.get(queue_id)

    def list(self) -> tuple[QueueEntry, ...]:
        return tuple(sorted(self._entries.values(), key=lambda entry: (entry.created_at, str(entry.queue_id))))
