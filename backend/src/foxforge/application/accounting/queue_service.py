# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from uuid import UUID

from foxforge.application.fleet import FleetService
from foxforge.application.queue import QueueEntry, QueueService, QueueStore

from .service import FilamentAccountingService


class AccountingQueueService(QueueService):
    """QueueService composition that applies P3 guards to every dispatch ingress."""

    def __init__(
        self,
        fleet: FleetService,
        store: QueueStore,
        accounting: FilamentAccountingService,
    ) -> None:
        super().__init__(fleet, store)
        self._accounting = accounting

    async def dispatch(self, queue_id: UUID) -> QueueEntry:
        self._accounting.verify_dispatch(self.get(queue_id))
        return await super().dispatch(queue_id)
