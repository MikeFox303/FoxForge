# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from foxforge.domain.printers import PrinterErrorCode
from foxforge.domain.printers.capabilities import (
    PrintDispatchReceipt,
    PrintExecutionAssessment,
    PrintExecutionRequest,
)
from foxforge.domain.printers.models import normalize_utc


class QueueEntryState(StrEnum):
    PENDING = "pending"
    BLOCKED = "blocked"
    DISPATCHING = "dispatching"
    ACCEPTED = "accepted"
    INDETERMINATE = "indeterminate"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class QueueDispatchError:
    code: PrinterErrorCode
    message: str
    retryable: bool
    vendor_code: str | None = None

    def __post_init__(self) -> None:
        if not self.message:
            raise ValueError("queue dispatch error message must not be empty")


@dataclass(frozen=True, slots=True)
class QueueEntry:
    queue_id: UUID
    printer_id: str
    request: PrintExecutionRequest
    state: QueueEntryState
    created_at: datetime
    updated_at: datetime
    assessment: PrintExecutionAssessment | None = None
    receipt: PrintDispatchReceipt | None = None
    error: QueueDispatchError | None = None
    attempt_count: int = 0
    last_attempt_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.printer_id:
            raise ValueError("printer_id must not be empty")
        if self.attempt_count < 0:
            raise ValueError("attempt_count must be non-negative")

        object.__setattr__(self, "created_at", normalize_utc(self.created_at, field_name="created_at"))
        object.__setattr__(self, "updated_at", normalize_utc(self.updated_at, field_name="updated_at"))
        if self.last_attempt_at is not None:
            object.__setattr__(
                self,
                "last_attempt_at",
                normalize_utc(self.last_attempt_at, field_name="last_attempt_at"),
            )

        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.attempt_count == 0 and self.last_attempt_at is not None:
            raise ValueError("last_attempt_at requires at least one dispatch attempt")
        if self.attempt_count > 0 and self.last_attempt_at is None:
            raise ValueError("dispatch attempts require last_attempt_at")

        if self.receipt is not None:
            if self.receipt.dispatch_id != self.request.dispatch_id:
                raise ValueError("receipt dispatch_id must match queue request")
            if self.receipt.artifact_sha256 != self.request.artifact.sha256:
                raise ValueError("receipt artifact fingerprint must match queue request")

        if self.state == QueueEntryState.ACCEPTED and self.receipt is None:
            raise ValueError("accepted queue entries require a dispatch receipt")
        if self.state != QueueEntryState.ACCEPTED and self.receipt is not None:
            raise ValueError("dispatch receipt is only valid for accepted queue entries")
        if self.state == QueueEntryState.INDETERMINATE:
            if self.error is None or self.error.code != PrinterErrorCode.INDETERMINATE:
                raise ValueError("indeterminate queue entries require an INDETERMINATE error")
