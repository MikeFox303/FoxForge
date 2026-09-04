# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path

from foxforge.application.accounting import (
    AccountingQueueService,
    FilamentAccountingService,
    InMemoryFilamentAccountingStore,
    MaterialEstimate,
)
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueEntryState
from foxforge.domain.printers.capabilities import (
    LocalPrintArtifact,
    MaterialBinding,
    PrintArtifactFormat,
    PrintAssessmentBlockerCode,
)


def test_dispatch_is_durably_blocked_when_reserved_spool_left_slot() -> None:
    async def scenario() -> None:
        inventory = InventoryService(InMemoryInventoryStore())
        spool = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("100"))
        inventory.assign_spool(spool.spool_id, "printer-1", "slot-0")
        accounting = FilamentAccountingService(inventory, InMemoryFilamentAccountingStore())
        queue = AccountingQueueService(FleetService(), InMemoryQueueStore(), accounting)
        entry = queue.enqueue(
            "printer-1",
            LocalPrintArtifact(
                artifact_id="a" * 64,
                path=Path("/data/artifacts/job.gcode"),
                filename="job.gcode",
                format=PrintArtifactFormat.GCODE,
                size_bytes=10,
                sha256="a" * 64,
            ),
            material_bindings=(MaterialBinding(material_index=0, slot_id="slot-0"),),
        )
        accounting.plan(entry, (MaterialEstimate(0, Decimal("25")),))
        inventory.unassign_spool(spool.spool_id)

        blocked = await queue.dispatch(entry.queue_id)

        assert blocked.state == QueueEntryState.BLOCKED
        assert blocked.receipt is None
        assert blocked.attempt_count == 0
        assert blocked.assessment is not None
        assert blocked.assessment.eligible is False
        assert blocked.assessment.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE
        assert "no longer assigned" in (blocked.assessment.blockers[0].message or "")
        assert queue.get(entry.queue_id) == blocked

    asyncio.run(scenario())
