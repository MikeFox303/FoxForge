# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from .models import PrinterId, normalize_utc


class PrinterEventKind(StrEnum):
    CONNECTION_CHANGED = "connection_changed"
    PRINTER_STATE_CHANGED = "printer_state_changed"
    JOB_STATE_CHANGED = "job_state_changed"
    JOB_PROGRESS_CHANGED = "job_progress_changed"
    CAPABILITY_CHANGED = "capability_changed"
    MATERIAL_SYSTEM_CHANGED = "material_system_changed"
    MATERIAL_TOPOLOGY_CHANGED = "material_topology_changed"
    SNAPSHOT_RECONCILED = "snapshot_reconciled"


@dataclass(frozen=True, slots=True)
class PrinterEvent:
    event_id: UUID
    printer_id: PrinterId
    connection_epoch: UUID
    sequence: int
    observed_at: datetime
    emitted_at: datetime
    kind: PrinterEventKind
    payload: object

    def __post_init__(self) -> None:
        if not self.printer_id:
            raise ValueError("printer_id must not be empty")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        object.__setattr__(self, "observed_at", normalize_utc(self.observed_at, field_name="observed_at"))
        object.__setattr__(self, "emitted_at", normalize_utc(self.emitted_at, field_name="emitted_at"))
