# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from foxforge.application.accounting import (
    FilamentAccountingService,
    FilamentPlanConflictError,
    InMemoryFilamentAccountingStore,
    MaterialEstimate,
)
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import QueueEntry, QueueEntryState
from foxforge.domain.printers.capabilities import MaterialBinding, PrintDispatchReceipt, PrintExecutionRequest
from tests.helpers import make_artifact


def _entry(tmp_path) -> QueueEntry:
    now = datetime.now(UTC)
    artifact = make_artifact(tmp_path / "plan-lifecycle.gcode")
    return QueueEntry(
        queue_id=uuid4(),
        printer_id="printer-1",
        request=PrintExecutionRequest(
            dispatch_id=uuid4(),
            artifact=artifact,
            material_bindings=(MaterialBinding(0, "slot-1"),),
        ),
        state=QueueEntryState.PENDING,
        created_at=now,
        updated_at=now,
    )


def _services():
    inventory = InventoryService(InMemoryInventoryStore())
    spool = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal("100"))
    inventory.assign_spool(spool.spool_id, "printer-1", "slot-1")
    accounting = FilamentAccountingService(inventory, InMemoryFilamentAccountingStore())
    return accounting


def _receipt(entry: QueueEntry) -> PrintDispatchReceipt:
    return PrintDispatchReceipt(
        dispatch_id=entry.request.dispatch_id,
        accepted_at=datetime.now(UTC),
        vendor_job_id="job-1",
        artifact_sha256=entry.request.artifact.sha256,
    )


@pytest.mark.parametrize("terminal", ["released", "consumed", "reconciliation_required"])
def test_terminal_reservation_cannot_be_replanned(tmp_path, terminal: str) -> None:
    accounting = _services()
    entry = _entry(tmp_path)
    estimate = (MaterialEstimate(0, Decimal("20")),)
    accounting.plan(entry, estimate)

    if terminal == "released":
        accounting.release_unstarted(entry)
    elif terminal == "consumed":
        accounting.sync_queue_entry(
            replace(
                entry,
                state=QueueEntryState.COMPLETED,
                receipt=_receipt(entry),
                updated_at=datetime.now(UTC),
            )
        )
    else:
        accounting.sync_queue_entry(
            replace(
                entry,
                state=QueueEntryState.CANCELLED,
                receipt=_receipt(entry),
                updated_at=datetime.now(UTC),
            )
        )

    with pytest.raises(FilamentPlanConflictError, match="new queue entry"):
        accounting.plan(entry, estimate)
