# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid4

from foxforge.application.fleet import FleetService
from foxforge.domain.printers import PrinterAdapterError, PrinterErrorCode, utc_now
from foxforge.domain.printers.capabilities import (
    LocalPrintArtifact,
    MaterialBinding,
    PrintArtifactSelection,
    PrintAssessmentBlocker,
    PrintAssessmentBlockerCode,
    PrintDispatchReceipt,
    PrintExecutionAssessment,
    PrintExecutionCapability,
    PrintExecutionRequest,
)

from .models import QueueDispatchError, QueueEntry, QueueEntryState
from .store import QueueStore


class QueueEntryNotFoundError(KeyError):
    def __init__(self, queue_id: UUID) -> None:
        self.queue_id = queue_id
        super().__init__(str(queue_id))


class QueueReconciliationRequiredError(RuntimeError):
    def __init__(self, entry: QueueEntry) -> None:
        self.entry = entry
        super().__init__(
            f"queue entry {entry.queue_id} is {entry.state.value}; reconcile the previous dispatch before retrying"
        )


class QueueService:
    """Durable-idempotency state machine for automated print dispatch.

    QueueService never sees a concrete printer adapter. It resolves the common
    PrintExecutionCapability through FleetService and persists the dispatch
    state before any submit side effect can occur.
    """

    def __init__(self, fleet: FleetService, store: QueueStore) -> None:
        self._fleet = fleet
        self._store = store

    def enqueue(
        self,
        printer_id: str,
        artifact: LocalPrintArtifact,
        *,
        selection: PrintArtifactSelection | None = None,
        material_bindings: tuple[MaterialBinding, ...] = (),
        requested_name: str | None = None,
        queue_id: UUID | None = None,
        dispatch_id: UUID | None = None,
    ) -> QueueEntry:
        now = utc_now()
        request = PrintExecutionRequest(
            dispatch_id=dispatch_id or uuid4(),
            artifact=artifact,
            selection=selection,
            material_bindings=material_bindings,
            requested_name=requested_name,
        )
        entry = QueueEntry(
            queue_id=queue_id or uuid4(),
            printer_id=printer_id,
            request=request,
            state=QueueEntryState.PENDING,
            created_at=now,
            updated_at=now,
        )
        # Normative ordering: the queue owns durable dispatch_id persistence and
        # must write it before assess/submit can interact with the adapter.
        self._store.create(entry)
        return entry

    def get(self, queue_id: UUID) -> QueueEntry:
        return self._require_entry(queue_id)

    def list(self) -> tuple[QueueEntry, ...]:
        return self._store.list()

    async def assess(self, queue_id: UUID) -> QueueEntry:
        entry = self._require_entry(queue_id)
        if entry.state in {QueueEntryState.DISPATCHING, QueueEntryState.INDETERMINATE}:
            raise QueueReconciliationRequiredError(entry)
        if entry.state == QueueEntryState.ACCEPTED:
            return entry

        capability = self._fleet.capability(entry.printer_id, PrintExecutionCapability)
        if capability is None:
            assessment = PrintExecutionAssessment(
                eligible=False,
                blockers=(
                    PrintAssessmentBlocker(
                        PrintAssessmentBlockerCode.UNKNOWN,
                        "printer does not expose foxforge.print_execution v1",
                    ),
                ),
                observed_at=utc_now(),
            )
        else:
            assessment = await capability.assess(entry.request)

        next_state = QueueEntryState.PENDING if assessment.eligible else QueueEntryState.BLOCKED
        updated = replace(
            entry,
            state=next_state,
            assessment=assessment,
            error=None,
            updated_at=utc_now(),
        )
        self._store.save(updated)
        return updated

    async def dispatch(self, queue_id: UUID) -> QueueEntry:
        entry = self._require_entry(queue_id)
        if entry.state == QueueEntryState.ACCEPTED:
            return entry
        if entry.state in {QueueEntryState.DISPATCHING, QueueEntryState.INDETERMINATE}:
            raise QueueReconciliationRequiredError(entry)

        assessed = await self.assess(queue_id)
        if assessed.state == QueueEntryState.BLOCKED:
            return assessed

        capability = self._fleet.capability(assessed.printer_id, PrintExecutionCapability)
        if capability is None:
            # assess() already turns this into BLOCKED; this protects against a
            # capability disappearing between assessment and submission.
            return await self.assess(queue_id)

        attempt_time = utc_now()
        dispatching = replace(
            assessed,
            state=QueueEntryState.DISPATCHING,
            receipt=None,
            error=None,
            attempt_count=assessed.attempt_count + 1,
            last_attempt_at=attempt_time,
            updated_at=attempt_time,
        )
        self._store.save(dispatching)

        try:
            receipt = await capability.submit(dispatching.request)
        except PrinterAdapterError as error:
            queue_error = QueueDispatchError(
                code=error.code,
                message=error.message,
                retryable=error.retryable,
                vendor_code=error.vendor_code,
            )
            next_state = (
                QueueEntryState.INDETERMINATE
                if error.code == PrinterErrorCode.INDETERMINATE
                else QueueEntryState.FAILED
            )
            failed = replace(
                dispatching,
                state=next_state,
                error=queue_error,
                updated_at=utc_now(),
            )
            self._store.save(failed)
            return failed

        if receipt.dispatch_id != dispatching.request.dispatch_id:
            return self._record_contract_failure(dispatching, "adapter returned a receipt for a different dispatch_id")
        if receipt.artifact_sha256 != dispatching.request.artifact.sha256:
            return self._record_contract_failure(dispatching, "adapter returned a receipt for a different artifact")

        accepted = replace(
            dispatching,
            state=QueueEntryState.ACCEPTED,
            receipt=receipt,
            error=None,
            updated_at=utc_now(),
        )
        self._store.save(accepted)
        return accepted

    def resolve_reconciliation(
        self,
        queue_id: UUID,
        *,
        accepted: bool,
        vendor_job_id: str | None = None,
        accepted_at: datetime | None = None,
    ) -> QueueEntry:
        """Persist an externally reconciled outcome for an uncertain dispatch.

        The caller must establish the outcome from current printer/job state or
        another trusted reconciliation mechanism. This method deliberately does
        not guess from vendor-specific fields.
        """

        entry = self._require_entry(queue_id)
        if entry.state not in {QueueEntryState.DISPATCHING, QueueEntryState.INDETERMINATE}:
            raise ValueError("only dispatching or indeterminate entries can be reconciled")

        now = utc_now()
        if accepted:
            receipt = PrintDispatchReceipt(
                dispatch_id=entry.request.dispatch_id,
                accepted_at=accepted_at or now,
                vendor_job_id=vendor_job_id,
                artifact_sha256=entry.request.artifact.sha256,
            )
            resolved = replace(
                entry,
                state=QueueEntryState.ACCEPTED,
                receipt=receipt,
                error=None,
                updated_at=now,
            )
        else:
            resolved = replace(
                entry,
                state=QueueEntryState.PENDING,
                receipt=None,
                error=None,
                assessment=None,
                updated_at=now,
            )

        self._store.save(resolved)
        return resolved

    def _require_entry(self, queue_id: UUID) -> QueueEntry:
        entry = self._store.get(queue_id)
        if entry is None:
            raise QueueEntryNotFoundError(queue_id)
        return entry

    def _record_contract_failure(self, entry: QueueEntry, message: str) -> QueueEntry:
        failed = replace(
            entry,
            state=QueueEntryState.FAILED,
            error=QueueDispatchError(
                code=PrinterErrorCode.INTERNAL_ADAPTER_ERROR,
                message=message,
                retryable=False,
            ),
            updated_at=utc_now(),
        )
        self._store.save(failed)
        return failed
