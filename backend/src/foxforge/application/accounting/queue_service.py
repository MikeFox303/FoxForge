# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from foxforge.application.fleet import FleetService
from foxforge.application.queue import QueueEntry, QueueEntryState, QueueService, QueueStore
from foxforge.domain.printers import utc_now
from foxforge.domain.printers.capabilities import (
    PrintAssessmentBlocker,
    PrintAssessmentBlockerCode,
    PrintExecutionAssessment,
)

from .service import FilamentAccountingError, FilamentAccountingService


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
        entry = self.get(queue_id)
        try:
            self._accounting.verify_dispatch(entry)
        except FilamentAccountingError as error:
            observed_at = utc_now()
            blocked = replace(
                entry,
                state=QueueEntryState.BLOCKED,
                assessment=PrintExecutionAssessment(
                    eligible=False,
                    blockers=(
                        PrintAssessmentBlocker(
                            PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                            str(error),
                        ),
                    ),
                    observed_at=observed_at,
                ),
                error=None,
                updated_at=observed_at,
            )
            self._store.save(blocked)
            return blocked
        return await super().dispatch(queue_id)
