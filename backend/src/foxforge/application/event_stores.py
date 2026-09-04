# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from uuid import UUID

from foxforge.domain.inventory import Spool, SpoolAdjustment, SpoolAssignment

from .events import ApplicationEventJournal, ApplicationEventTopic
from .inventory.store import AdjustmentWriteResult, InventoryStore
from .queue.models import QueueEntry
from .queue.store import QueueStore


class EventingQueueStore:
    """Publish queue invalidation events only after durable store writes succeed."""

    def __init__(self, inner: QueueStore, journal: ApplicationEventJournal) -> None:
        self._inner = inner
        self._journal = journal

    def create(self, entry: QueueEntry) -> None:
        self._inner.create(entry)
        self._changed(entry)

    def save(self, entry: QueueEntry) -> None:
        self._inner.save(entry)
        self._changed(entry)

    def get(self, queue_id: UUID) -> QueueEntry | None:
        return self._inner.get(queue_id)

    def list(self) -> tuple[QueueEntry, ...]:
        return self._inner.list()

    def _changed(self, entry: QueueEntry) -> None:
        self._journal.publish(
            ApplicationEventTopic.QUEUE,
            "entry_changed",
            resource_id=str(entry.queue_id),
        )


class EventingInventoryStore:
    """Publish inventory invalidation events only after durable mutations succeed."""

    def __init__(self, inner: InventoryStore, journal: ApplicationEventJournal) -> None:
        self._inner = inner
        self._journal = journal

    def create_spool(self, spool: Spool) -> None:
        self._inner.create_spool(spool)
        self._changed(spool.spool_id, "spool_changed")

    def save_spool(self, spool: Spool) -> None:
        self._inner.save_spool(spool)
        self._changed(spool.spool_id, "spool_changed")

    def get_spool(self, spool_id: UUID) -> Spool | None:
        return self._inner.get_spool(spool_id)

    def list_spools(self) -> tuple[Spool, ...]:
        return self._inner.list_spools()

    def append_adjustment(self, adjustment: SpoolAdjustment) -> AdjustmentWriteResult:
        result = self._inner.append_adjustment(adjustment)
        if result.created:
            self._changed(result.adjustment.spool_id, "balance_changed")
        return result

    def get_adjustment_by_key(self, idempotency_key: str) -> SpoolAdjustment | None:
        return self._inner.get_adjustment_by_key(idempotency_key)

    def list_adjustments(self, spool_id: UUID) -> tuple[SpoolAdjustment, ...]:
        return self._inner.list_adjustments(spool_id)

    def save_assignment(self, assignment: SpoolAssignment) -> None:
        self._inner.save_assignment(assignment)
        self._changed(assignment.spool_id, "assignment_changed")

    def delete_assignment(self, spool_id: UUID) -> None:
        self._inner.delete_assignment(spool_id)
        self._changed(spool_id, "assignment_changed")

    def assignment_for_spool(self, spool_id: UUID) -> SpoolAssignment | None:
        return self._inner.assignment_for_spool(spool_id)

    def assignment_for_slot(self, printer_id: str, slot_id: str) -> SpoolAssignment | None:
        return self._inner.assignment_for_slot(printer_id, slot_id)

    def list_assignments(self) -> tuple[SpoolAssignment, ...]:
        return self._inner.list_assignments()

    def _changed(self, spool_id: UUID, change: str) -> None:
        self._journal.publish(
            ApplicationEventTopic.INVENTORY,
            change,
            resource_id=str(spool_id),
        )
