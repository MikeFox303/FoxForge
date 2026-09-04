# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from uuid import UUID

from foxforge.application.queue import QueueEntry, QueueStore

from .service import FilamentAccountingService


class AccountingQueueStore:
    """QueueStore decorator that settles accounting after durable queue writes."""

    def __init__(self, delegate: QueueStore, accounting: FilamentAccountingService) -> None:
        self._delegate = delegate
        self._accounting = accounting

    def create(self, entry: QueueEntry) -> None:
        self._delegate.create(entry)
        self._accounting.sync_queue_entry(entry)

    def save(self, entry: QueueEntry) -> None:
        self._delegate.save(entry)
        self._accounting.sync_queue_entry(entry)

    def get(self, queue_id: UUID) -> QueueEntry | None:
        return self._delegate.get(queue_id)

    def list(self) -> tuple[QueueEntry, ...]:
        return self._delegate.list()
