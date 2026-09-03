# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid4

from foxforge.application.fleet import FleetService
from foxforge.domain.printers import (
    ActiveJobSnapshot,
    JobState,
    PrinterAdapterError,
    PrinterErrorCode,
    PrinterEvent,
    PrinterEventKind,
    utc_now,
)
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


_JOB_STATE_TO_QUEUE_STATE = {
    JobState.ACCEPTED: QueueEntryState.ACCEPTED,
    JobState.PREPARING: QueueEntryState.PREPARING,
    JobState.PRINTING: QueueEntryState.PRINTING,
    JobState.PAUSED: QueueEntryState.PAUSED,
    JobState.COMPLETED: QueueEntryState.COMPLETED,
    JobState.FAILED: QueueEntryState.FAILED,
    JobState.CANCELLED: QueueEntryState.CANCELLED,
}
_ALLOWED_LIFECYCLE_TRANSITIONS = {
    QueueEntryState.ACCEPTED: frozenset(
        {
            QueueEntryState.ACCEPTED,
            QueueEntryState.PREPARING,
            QueueEntryState.PRINTING,
            QueueEntryState.PAUSED,
            QueueEntryState.COMPLETED,
            QueueEntryState.FAILED,
            QueueEntryState.CANCELLED,
        }
    ),
    QueueEntryState.PREPARING: frozenset(
        {
            QueueEntryState.PREPARING,
            QueueEntryState.PRINTING,
            QueueEntryState.PAUSED,
            QueueEntryState.COMPLETED,
            QueueEntryState.FAILED,
            QueueEntryState.CANCELLED,
        }
    ),
    QueueEntryState.PRINTING: frozenset(
        {
            QueueEntryState.PRINTING,
            QueueEntryState.PAUSED,
            QueueEntryState.COMPLETED,
            QueueEntryState.FAILED,
            QueueEntryState.CANCELLED,
        }
    ),
    QueueEntryState.PAUSED: frozenset(
        {
            QueueEntryState.PAUSED,
            QueueEntryState.PRINTING,
            QueueEntryState.COMPLETED,
            QueueEntryState.FAILED,
            QueueEntryState.CANCELLED,
        }
    ),
    QueueEntryState.COMPLETED: frozenset({QueueEntryState.COMPLETED}),
    QueueEntryState.CANCELLED: frozenset({QueueEntryState.CANCELLED}),
    QueueEntryState.FAILED: frozenset({QueueEntryState.FAILED}),
}


class QueueService:
    """Durable-idempotency state machine for automated print dispatch.

    QueueService never sees a concrete printer adapter. It resolves the common
    PrintExecutionCapability through FleetService, persists dispatch state
    before any submit side effect can occur, and tracks confirmed remote jobs
    only through normalized fleet events.
    """

    def __init__(self, fleet: FleetService, store: QueueStore) -> None:
        self._fleet = fleet
        self._store = store
        self._event_task: asyncio.Task[None] | None = None
        self._event_ready: asyncio.Event | None = None

    async def start(self) -> None:
        """Start normalized fleet-event tracking and reconcile live snapshots.

        Composition roots should call this during application startup so queue
        entries restored from durable storage resume lifecycle tracking without
        requiring a new dispatch call. dispatch() also calls start() lazily.
        """

        task = self._event_task
        if task is None or task.done():
            self._event_ready = asyncio.Event()
            self._event_task = asyncio.create_task(self._track_fleet_events())
        assert self._event_ready is not None
        await self._event_ready.wait()
        self._reconcile_current_snapshots()

    async def aclose(self) -> None:
        task = self._event_task
        self._event_task = None
        self._event_ready = None
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

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
        if entry.receipt is not None:
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
        await self.start()
        entry = self._require_entry(queue_id)
        if entry.receipt is not None:
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
        # submit() may have emitted ACCEPTED before the durable receipt was
        # stored. Reconcile the current common snapshot now so later tracking
        # starts from a known job identity without relying on event timing.
        self._reconcile_printer_snapshot(accepted.printer_id)
        return self._require_entry(queue_id)

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
        if resolved.receipt is not None:
            self._reconcile_printer_snapshot(resolved.printer_id)
            return self._require_entry(queue_id)
        return resolved

    async def _track_fleet_events(self) -> None:
        stream = self._fleet.events()
        assert self._event_ready is not None
        self._event_ready.set()
        try:
            async for event in stream:
                self._process_event(event)
        except asyncio.CancelledError:
            raise
        finally:
            close = getattr(stream, "aclose", None)
            if close is not None:
                await close()

    def _process_event(self, event: PrinterEvent) -> tuple[QueueEntry, ...]:
        if event.kind != PrinterEventKind.JOB_STATE_CHANGED:
            return ()
        job = event.payload
        if not isinstance(job, ActiveJobSnapshot) or job.vendor_job_id is None:
            return ()
        return self._apply_job_observation(event.printer_id, job, event.observed_at)

    def _reconcile_current_snapshots(self) -> None:
        tracked_printers = {
            entry.printer_id
            for entry in self._store.list()
            if entry.receipt is not None and entry.receipt.vendor_job_id is not None and not entry.terminal
        }
        for printer_id in sorted(tracked_printers):
            self._reconcile_printer_snapshot(printer_id)

    def _reconcile_printer_snapshot(self, printer_id: str) -> tuple[QueueEntry, ...]:
        if printer_id not in self._fleet.printer_ids:
            return ()
        snapshot = self._fleet.snapshot(printer_id)
        job = snapshot.active_job
        if job is None or job.vendor_job_id is None:
            return ()
        return self._apply_job_observation(printer_id, job, snapshot.observed_at)

    def _apply_job_observation(
        self,
        printer_id: str,
        job: ActiveJobSnapshot,
        observed_at: datetime,
    ) -> tuple[QueueEntry, ...]:
        if job.vendor_job_id is None:
            return ()
        target_state = _JOB_STATE_TO_QUEUE_STATE.get(job.state)
        if target_state is None:
            return ()

        changed: list[QueueEntry] = []
        for entry in self._store.list():
            receipt = entry.receipt
            if entry.printer_id != printer_id or receipt is None:
                continue
            if receipt.vendor_job_id is None or receipt.vendor_job_id != job.vendor_job_id:
                continue
            if observed_at < receipt.accepted_at or observed_at < entry.updated_at:
                continue

            allowed = _ALLOWED_LIFECYCLE_TRANSITIONS.get(entry.state)
            if allowed is None or target_state not in allowed:
                continue

            updated = replace(
                entry,
                state=target_state,
                error=None if target_state != QueueEntryState.FAILED else entry.error,
                updated_at=observed_at,
            )
            if updated == entry:
                continue
            self._store.save(updated)
            changed.append(updated)

        return tuple(changed)

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
