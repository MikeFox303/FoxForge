# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import TypeVar, cast
from uuid import UUID, uuid4

from foxforge.domain.printers import (
    ActiveJobSnapshot,
    ConnectionState,
    JobState,
    OperationalState,
    PrinterAdapterError,
    PrinterErrorCode,
    PrinterEvent,
    PrinterEventKind,
    PrinterIdentity,
    PrinterSnapshot,
    utc_now,
)
from foxforge.domain.printers.capabilities import (
    MATERIAL_SYSTEM_CAPABILITY_ID,
    MATERIAL_SYSTEM_MAJOR_VERSION,
    PRINT_EXECUTION_CAPABILITY_ID,
    PRINT_EXECUTION_MAJOR_VERSION,
    LocalPrintArtifact,
    MaterialActivity,
    MaterialPresence,
    MaterialSystemCapability,
    MaterialSystemDescriptor,
    MaterialSystemSnapshot,
    PrintArtifactFormat,
    PrintAssessmentBlocker,
    PrintAssessmentBlockerCode,
    PrintDispatchReceipt,
    PrintExecutionAssessment,
    PrintExecutionCapability,
    PrintExecutionDescriptor,
    PrintExecutionRequest,
)

C = TypeVar("C")


class _FakeEventSubscription(AsyncIterator[PrinterEvent]):
    def __init__(self, adapter: FakePrinterAdapter) -> None:
        self._adapter = adapter
        self._queue: asyncio.Queue[PrinterEvent] = asyncio.Queue()
        self._closed = False
        adapter._subscribers.add(self._queue)

    def __aiter__(self) -> _FakeEventSubscription:
        return self

    async def __anext__(self) -> PrinterEvent:
        if self._closed:
            raise StopAsyncIteration
        return await self._queue.get()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._adapter._subscribers.discard(self._queue)


class FakePrinterAdapter:
    """Deterministic in-memory adapter used by shared contract and application tests."""

    def __init__(self, identity: PrinterIdentity) -> None:
        self._identity = identity
        self._snapshot = PrinterSnapshot(
            printer_id=identity.printer_id,
            connection=ConnectionState.DISCONNECTED,
            operational_state=OperationalState.OFFLINE,
            active_job=None,
            observed_at=utc_now(),
            stale=False,
        )
        self._capabilities: dict[type[object], object] = {}
        self._subscribers: set[asyncio.Queue[PrinterEvent]] = set()
        self._connection_epoch = uuid4()
        self._sequence = 0
        self.transport_connect_count = 0
        self.transport_disconnect_count = 0

    @property
    def identity(self) -> PrinterIdentity:
        return self._identity

    async def connect(self) -> None:
        if self._snapshot.connection in {ConnectionState.CONNECTED, ConnectionState.DEGRADED}:
            return
        self.transport_connect_count += 1
        self._connection_epoch = uuid4()
        self._sequence = 0
        self._snapshot = replace(
            self._snapshot,
            connection=ConnectionState.CONNECTED,
            operational_state=OperationalState.IDLE,
            active_job=None,
            observed_at=utc_now(),
            stale=False,
        )
        self._emit(PrinterEventKind.CONNECTION_CHANGED, self._snapshot)
        self._emit(PrinterEventKind.SNAPSHOT_RECONCILED, self._snapshot)

    async def disconnect(self) -> None:
        if self._snapshot.connection == ConnectionState.DISCONNECTED:
            return
        self.transport_disconnect_count += 1
        self._snapshot = replace(
            self._snapshot,
            connection=ConnectionState.DISCONNECTED,
            operational_state=OperationalState.OFFLINE,
            active_job=None,
            observed_at=utc_now(),
            stale=False,
        )
        self._emit(PrinterEventKind.CONNECTION_CHANGED, self._snapshot)

    def snapshot(self) -> PrinterSnapshot:
        return self._snapshot

    def capability(self, capability_type: type[C]) -> C | None:
        value = self._capabilities.get(cast(type[object], capability_type))
        return cast(C | None, value)

    def events(self) -> AsyncIterator[PrinterEvent]:
        return _FakeEventSubscription(self)

    def register_capability(self, capability_type: type[C], capability: C) -> None:
        previous = self._capabilities.get(cast(type[object], capability_type))
        self._capabilities[cast(type[object], capability_type)] = capability
        if previous is not capability and self._snapshot.connection != ConnectionState.DISCONNECTED:
            self._emit(PrinterEventKind.CAPABILITY_CHANGED, capability_type.__name__)

    def remove_capability(self, capability_type: type[object]) -> None:
        removed = self._capabilities.pop(capability_type, None)
        if removed is not None and self._snapshot.connection != ConnectionState.DISCONNECTED:
            self._emit(PrinterEventKind.CAPABILITY_CHANGED, capability_type.__name__)

    def set_snapshot(self, snapshot: PrinterSnapshot) -> None:
        if snapshot.printer_id != self._identity.printer_id:
            raise ValueError("snapshot printer_id must match adapter identity")
        previous = self._snapshot
        self._snapshot = snapshot
        if previous.operational_state != snapshot.operational_state:
            self._emit(PrinterEventKind.PRINTER_STATE_CHANGED, snapshot)
        if (previous.active_job and previous.active_job.state) != (snapshot.active_job and snapshot.active_job.state):
            self._emit(PrinterEventKind.JOB_STATE_CHANGED, snapshot.active_job)
        previous_progress = previous.active_job.progress if previous.active_job else None
        current_progress = snapshot.active_job.progress if snapshot.active_job else None
        if previous_progress != current_progress:
            self._emit(PrinterEventKind.JOB_PROGRESS_CHANGED, snapshot.active_job)

    def set_operational_state(self, state: OperationalState) -> None:
        self.set_snapshot(replace(self._snapshot, operational_state=state, observed_at=utc_now()))

    def set_active_job(
        self,
        job: ActiveJobSnapshot | None,
        *,
        operational_state: OperationalState | None = None,
    ) -> None:
        self.set_snapshot(
            replace(
                self._snapshot,
                active_job=job,
                operational_state=operational_state or self._snapshot.operational_state,
                observed_at=utc_now(),
            )
        )

    def _emit(self, kind: PrinterEventKind, payload: object) -> PrinterEvent:
        self._sequence += 1
        now = utc_now()
        event = PrinterEvent(
            event_id=uuid4(),
            printer_id=self._identity.printer_id,
            connection_epoch=self._connection_epoch,
            sequence=self._sequence,
            observed_at=now,
            emitted_at=now,
            kind=kind,
            payload=payload,
        )
        for queue in tuple(self._subscribers):
            queue.put_nowait(event)
        return event


class FakeMaterialSystemCapability:
    """Read-only material-system capability with explicit state injection for tests."""

    def __init__(
        self,
        adapter: FakePrinterAdapter,
        snapshot: MaterialSystemSnapshot,
        *,
        reports_active_source: bool = True,
        reports_remaining_fraction: bool = True,
        reports_material_identity: bool = True,
        reports_tag_identity: bool = True,
    ) -> None:
        if snapshot.printer_id != adapter.identity.printer_id:
            raise ValueError("material snapshot printer_id must match adapter")
        self._adapter = adapter
        self._snapshot = snapshot
        self._descriptor = MaterialSystemDescriptor(
            capability_id=MATERIAL_SYSTEM_CAPABILITY_ID,
            major_version=MATERIAL_SYSTEM_MAJOR_VERSION,
            reports_active_source=reports_active_source,
            reports_remaining_fraction=reports_remaining_fraction,
            reports_material_identity=reports_material_identity,
            reports_tag_identity=reports_tag_identity,
        )

    @property
    def descriptor(self) -> MaterialSystemDescriptor:
        return self._descriptor

    def snapshot(self) -> MaterialSystemSnapshot:
        return self._snapshot

    def set_snapshot(self, snapshot: MaterialSystemSnapshot) -> None:
        if snapshot.printer_id != self._adapter.identity.printer_id:
            raise ValueError("material snapshot printer_id must match adapter")
        self._snapshot = snapshot
        self._adapter._emit(PrinterEventKind.MATERIAL_SYSTEM_CHANGED, snapshot)


class FakePrintExecutionCapability:
    """Queue-facing fake with real v1 eligibility and idempotency semantics."""

    def __init__(
        self,
        adapter: FakePrinterAdapter,
        *,
        accepted_formats: frozenset[PrintArtifactFormat] = frozenset(
            {PrintArtifactFormat.GCODE, PrintArtifactFormat.THREE_MF}
        ),
        supports_plate_selection: bool = True,
        supports_material_bindings: bool = True,
        submit_delay_seconds: float = 0.0,
    ) -> None:
        self._adapter = adapter
        self._descriptor = PrintExecutionDescriptor(
            capability_id=PRINT_EXECUTION_CAPABILITY_ID,
            major_version=PRINT_EXECUTION_MAJOR_VERSION,
            accepted_formats=accepted_formats,
            supports_plate_selection=supports_plate_selection,
            supports_material_bindings=supports_material_bindings,
        )
        self.submit_delay_seconds = submit_delay_seconds
        self.assess_count = 0
        self.submit_attempt_count = 0
        self.start_count = 0
        self._receipts: dict[UUID, tuple[tuple[object, ...], PrintDispatchReceipt]] = {}
        self._indeterminate: dict[UUID, tuple[object, ...]] = {}
        self._next_error: PrinterAdapterError | None = None
        self._make_next_indeterminate = False

    @property
    def descriptor(self) -> PrintExecutionDescriptor:
        return self._descriptor

    async def assess(self, request: PrintExecutionRequest) -> PrintExecutionAssessment:
        self.assess_count += 1
        blockers: list[PrintAssessmentBlocker] = []
        printer = self._adapter.snapshot()

        if printer.connection not in {ConnectionState.CONNECTED, ConnectionState.DEGRADED}:
            blockers.append(PrintAssessmentBlocker(PrintAssessmentBlockerCode.OFFLINE, "printer is offline"))
        elif printer.operational_state in {
            OperationalState.PREPARING,
            OperationalState.PRINTING,
            OperationalState.PAUSED,
            OperationalState.CANCELLING,
        }:
            blockers.append(PrintAssessmentBlocker(PrintAssessmentBlockerCode.BUSY, "printer is busy"))
        elif printer.operational_state != OperationalState.IDLE:
            blockers.append(PrintAssessmentBlocker(PrintAssessmentBlockerCode.NOT_READY, "printer is not ready"))

        if request.artifact.format not in self._descriptor.accepted_formats:
            blockers.append(
                PrintAssessmentBlocker(
                    PrintAssessmentBlockerCode.UNSUPPORTED_ARTIFACT,
                    "artifact format is unsupported",
                )
            )
        elif not _artifact_is_readable_and_matches(request.artifact):
            blockers.append(
                PrintAssessmentBlocker(
                    PrintAssessmentBlockerCode.UNSUPPORTED_ARTIFACT,
                    "artifact is unavailable or invalid",
                )
            )

        has_plate_selection = request.selection is not None and request.selection.plate_index is not None
        if has_plate_selection and not self._descriptor.supports_plate_selection:
            blockers.append(
                PrintAssessmentBlocker(
                    PrintAssessmentBlockerCode.UNSUPPORTED_SELECTION,
                    "plate selection is unsupported",
                )
            )

        if request.material_bindings:
            if not self._descriptor.supports_material_bindings:
                blockers.append(
                    PrintAssessmentBlocker(
                        PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID,
                        "material bindings are unsupported",
                    )
                )
            else:
                self._assess_material_bindings(request, blockers)

        return PrintExecutionAssessment(eligible=not blockers, blockers=tuple(blockers), observed_at=utc_now())

    async def submit(self, request: PrintExecutionRequest) -> PrintDispatchReceipt:
        self.submit_attempt_count += 1
        fingerprint = _request_fingerprint(request)

        previous = self._receipts.get(request.dispatch_id)
        if previous is not None:
            previous_fingerprint, receipt = previous
            if previous_fingerprint != fingerprint:
                raise _conflict_error()
            return receipt

        uncertain_fingerprint = self._indeterminate.get(request.dispatch_id)
        if uncertain_fingerprint is not None:
            if uncertain_fingerprint != fingerprint:
                raise _conflict_error()
            raise PrinterAdapterError(
                PrinterErrorCode.INDETERMINATE,
                "previous submission outcome is still indeterminate",
                retryable=False,
            )

        assessment = await self.assess(request)
        if not assessment.eligible:
            raise _error_for_blocker(assessment.blockers[0])

        if self.submit_delay_seconds:
            await asyncio.sleep(self.submit_delay_seconds)

        if self._next_error is not None:
            error = self._next_error
            self._next_error = None
            raise error

        if self._make_next_indeterminate:
            self._make_next_indeterminate = False
            self.start_count += 1
            self._indeterminate[request.dispatch_id] = fingerprint
            raise PrinterAdapterError(
                PrinterErrorCode.INDETERMINATE,
                "fake start may have been accepted but acknowledgement was lost",
                retryable=False,
            )

        return self._accept(request, fingerprint)

    def fail_next_submit(self, error: PrinterAdapterError) -> None:
        self._next_error = error

    def make_next_submit_indeterminate(self) -> None:
        self._make_next_indeterminate = True

    def resolve_indeterminate(self, dispatch_id: UUID, *, accepted: bool) -> PrintDispatchReceipt | None:
        fingerprint = self._indeterminate.pop(dispatch_id, None)
        if fingerprint is None:
            raise KeyError(dispatch_id)
        if not accepted:
            return None
        artifact_sha256 = cast(str, fingerprint[0])
        receipt = PrintDispatchReceipt(
            dispatch_id=dispatch_id,
            accepted_at=utc_now(),
            vendor_job_id=f"fake:{dispatch_id}",
            artifact_sha256=artifact_sha256,
        )
        self._receipts[dispatch_id] = (fingerprint, receipt)
        return receipt

    def _accept(self, request: PrintExecutionRequest, fingerprint: tuple[object, ...]) -> PrintDispatchReceipt:
        self.start_count += 1
        receipt = PrintDispatchReceipt(
            dispatch_id=request.dispatch_id,
            accepted_at=utc_now(),
            vendor_job_id=f"fake:{request.dispatch_id}",
            artifact_sha256=request.artifact.sha256,
        )
        self._receipts[request.dispatch_id] = (fingerprint, receipt)
        self._adapter.set_active_job(
            ActiveJobSnapshot(
                vendor_job_id=receipt.vendor_job_id,
                name=request.requested_name or request.artifact.filename,
                state=JobState.ACCEPTED,
                progress=0.0,
                elapsed_seconds=0,
                remaining_seconds=None,
                current_layer=None,
                total_layers=None,
            ),
            operational_state=OperationalState.PREPARING,
        )
        return receipt

    def _assess_material_bindings(
        self,
        request: PrintExecutionRequest,
        blockers: list[PrintAssessmentBlocker],
    ) -> None:
        material_system = self._adapter.capability(MaterialSystemCapability)
        if material_system is None:
            blockers.append(
                PrintAssessmentBlocker(
                    PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID,
                    "printer has no material-system capability",
                )
            )
            return

        slots = {slot.slot_id: slot for unit in material_system.snapshot().units for slot in unit.slots}
        for binding in request.material_bindings:
            slot = slots.get(binding.slot_id)
            if slot is None:
                blockers.append(
                    PrintAssessmentBlocker(
                        PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID,
                        f"unknown material slot: {binding.slot_id}",
                    )
                )
            elif slot.presence != MaterialPresence.LOADED:
                blockers.append(
                    PrintAssessmentBlocker(
                        PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                        f"material slot is not loaded: {binding.slot_id}",
                    )
                )
            elif slot.activity == MaterialActivity.UNKNOWN:
                # Unknown activity is not a blocker: it means the adapter cannot report it.
                continue


def build_fake_printer(
    identity: PrinterIdentity,
    *,
    material_snapshot: MaterialSystemSnapshot | None = None,
    accepted_formats: frozenset[PrintArtifactFormat] = frozenset(
        {PrintArtifactFormat.GCODE, PrintArtifactFormat.THREE_MF}
    ),
    supports_plate_selection: bool = True,
    supports_material_bindings: bool = True,
) -> tuple[FakePrinterAdapter, FakePrintExecutionCapability, FakeMaterialSystemCapability | None]:
    """Create a fake adapter and register its common capabilities by protocol type."""
    adapter = FakePrinterAdapter(identity)
    material: FakeMaterialSystemCapability | None = None
    if material_snapshot is not None:
        material = FakeMaterialSystemCapability(adapter, material_snapshot)
        adapter.register_capability(MaterialSystemCapability, material)
    printing = FakePrintExecutionCapability(
        adapter,
        accepted_formats=accepted_formats,
        supports_plate_selection=supports_plate_selection,
        supports_material_bindings=supports_material_bindings,
    )
    adapter.register_capability(PrintExecutionCapability, printing)
    return adapter, printing, material


def _artifact_is_readable_and_matches(artifact: LocalPrintArtifact) -> bool:
    try:
        if not artifact.path.is_file() or not os.access(artifact.path, os.R_OK):
            return False
        if artifact.path.stat().st_size != artifact.size_bytes:
            return False
        digest = hashlib.sha256()
        with artifact.path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest() == artifact.sha256
    except OSError:
        return False


def _request_fingerprint(request: PrintExecutionRequest) -> tuple[object, ...]:
    plate_index = request.selection.plate_index if request.selection else None
    bindings = tuple(sorted((binding.material_index, binding.slot_id) for binding in request.material_bindings))
    return (
        request.artifact.sha256,
        request.artifact.format.value,
        plate_index,
        bindings,
        request.requested_name,
    )


def _conflict_error() -> PrinterAdapterError:
    return PrinterAdapterError(
        PrinterErrorCode.CONFLICT,
        "dispatch_id was reused with a materially different request",
        retryable=False,
    )


def _error_for_blocker(blocker: PrintAssessmentBlocker) -> PrinterAdapterError:
    mapping = {
        PrintAssessmentBlockerCode.OFFLINE: (PrinterErrorCode.CONNECTION_UNAVAILABLE, True),
        PrintAssessmentBlockerCode.BUSY: (PrinterErrorCode.BUSY, True),
        PrintAssessmentBlockerCode.NOT_READY: (PrinterErrorCode.NOT_READY, True),
        PrintAssessmentBlockerCode.UNSUPPORTED_ARTIFACT: (PrinterErrorCode.UNSUPPORTED, False),
        PrintAssessmentBlockerCode.UNSUPPORTED_SELECTION: (PrinterErrorCode.UNSUPPORTED, False),
        PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID: (PrinterErrorCode.INVALID_REQUEST, False),
        PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE: (PrinterErrorCode.NOT_READY, True),
        PrintAssessmentBlockerCode.UNKNOWN: (PrinterErrorCode.INVALID_REQUEST, False),
    }
    code, retryable = mapping[blocker.code]
    return PrinterAdapterError(code, blocker.message or blocker.code.value, retryable=retryable)
