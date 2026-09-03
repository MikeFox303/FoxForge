# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from uuid import UUID

from foxforge.domain.printers import (
    ConnectionState,
    OperationalState,
    PrinterAdapterError,
    PrinterErrorCode,
    PrinterSnapshot,
    utc_now,
)
from foxforge.domain.printers.capabilities import (
    PRINT_EXECUTION_CAPABILITY_ID,
    PRINT_EXECUTION_MAJOR_VERSION,
    PrintArtifactFormat,
    PrintAssessmentBlocker,
    PrintAssessmentBlockerCode,
    PrintDispatchReceipt,
    PrintExecutionAssessment,
    PrintExecutionDescriptor,
    PrintExecutionRequest,
)

from .mapping import MOONRAKER_EXTERNAL_SLOT_ID
from .native import MoonrakerNativePrintRequest
from .transport import MoonrakerTransport, MoonrakerTransportError, MoonrakerTransportErrorKind


class MoonrakerPrintExecutionCapability:
    """Translate common queue dispatch into Moonraker upload/start semantics."""

    def __init__(self, transport: MoonrakerTransport, printer_snapshot: Callable[[], PrinterSnapshot]) -> None:
        self._transport = transport
        self._printer_snapshot = printer_snapshot
        self._descriptor = PrintExecutionDescriptor(
            capability_id=PRINT_EXECUTION_CAPABILITY_ID,
            major_version=PRINT_EXECUTION_MAJOR_VERSION,
            accepted_formats=frozenset({PrintArtifactFormat.GCODE}),
            supports_plate_selection=False,
            supports_material_bindings=True,
        )
        self._confirmed: dict[UUID, tuple[tuple[object, ...], PrintDispatchReceipt]] = {}

    @property
    def descriptor(self) -> PrintExecutionDescriptor:
        return self._descriptor

    async def assess(self, request: PrintExecutionRequest) -> PrintExecutionAssessment:
        blockers: list[PrintAssessmentBlocker] = []
        snapshot = self._printer_snapshot()

        if snapshot.connection not in {ConnectionState.CONNECTED, ConnectionState.DEGRADED}:
            blockers.append(PrintAssessmentBlocker(PrintAssessmentBlockerCode.OFFLINE, "printer is offline"))
        elif snapshot.operational_state in {
            OperationalState.PREPARING,
            OperationalState.PRINTING,
            OperationalState.PAUSED,
            OperationalState.CANCELLING,
        }:
            blockers.append(PrintAssessmentBlocker(PrintAssessmentBlockerCode.BUSY, "printer is busy"))
        elif snapshot.operational_state not in {
            OperationalState.IDLE,
            OperationalState.COMPLETED,
            OperationalState.FAILED,
        }:
            blockers.append(PrintAssessmentBlocker(PrintAssessmentBlockerCode.NOT_READY, "printer is not ready"))

        if request.artifact.format not in self._descriptor.accepted_formats or not _artifact_matches(request):
            blockers.append(
                PrintAssessmentBlocker(
                    PrintAssessmentBlockerCode.UNSUPPORTED_ARTIFACT,
                    "Moonraker print execution requires a readable, unchanged G-code artifact",
                )
            )

        if request.selection is not None and request.selection.plate_index is not None:
            blockers.append(
                PrintAssessmentBlocker(
                    PrintAssessmentBlockerCode.UNSUPPORTED_SELECTION,
                    "Moonraker G-code execution does not support plate selection",
                )
            )

        for binding in request.material_bindings:
            if binding.material_index != 0 or binding.slot_id != MOONRAKER_EXTERNAL_SLOT_ID:
                blockers.append(
                    PrintAssessmentBlocker(
                        PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID,
                        f"unsupported Moonraker material binding: {binding.material_index} -> {binding.slot_id}",
                    )
                )

        return PrintExecutionAssessment(eligible=not blockers, blockers=tuple(blockers), observed_at=utc_now())

    async def submit(self, request: PrintExecutionRequest) -> PrintDispatchReceipt:
        fingerprint = _request_fingerprint(request)
        previous = self._confirmed.get(request.dispatch_id)
        if previous is not None:
            previous_fingerprint, receipt = previous
            if previous_fingerprint != fingerprint:
                raise PrinterAdapterError(
                    PrinterErrorCode.CONFLICT,
                    "dispatch_id was reused with a materially different request",
                    retryable=False,
                )
            return receipt

        assessment = await self.assess(request)
        if not assessment.eligible:
            raise _error_for_blocker(assessment.blockers[0])

        native_request = MoonrakerNativePrintRequest(
            local_path=request.artifact.path,
            filename=request.artifact.filename,
            sha256=request.artifact.sha256,
        )
        try:
            result = await self._transport.submit_print(native_request)
        except MoonrakerTransportError as error:
            raise normalize_moonraker_transport_error(error) from error

        receipt = PrintDispatchReceipt(
            dispatch_id=request.dispatch_id,
            accepted_at=result.accepted_at,
            vendor_job_id=result.vendor_job_id,
            artifact_sha256=request.artifact.sha256,
        )
        self._confirmed[request.dispatch_id] = (fingerprint, receipt)
        return receipt


def normalize_moonraker_transport_error(error: MoonrakerTransportError) -> PrinterAdapterError:
    mapping = {
        MoonrakerTransportErrorKind.UNAVAILABLE: (PrinterErrorCode.CONNECTION_UNAVAILABLE, True),
        MoonrakerTransportErrorKind.AUTHENTICATION: (PrinterErrorCode.AUTHENTICATION_FAILED, False),
        MoonrakerTransportErrorKind.TIMEOUT: (PrinterErrorCode.TIMEOUT, True),
        MoonrakerTransportErrorKind.BUSY: (PrinterErrorCode.BUSY, True),
        MoonrakerTransportErrorKind.REJECTED: (PrinterErrorCode.REMOTE_REJECTED, False),
        MoonrakerTransportErrorKind.INDETERMINATE: (PrinterErrorCode.INDETERMINATE, False),
        MoonrakerTransportErrorKind.INTERNAL: (PrinterErrorCode.INTERNAL_ADAPTER_ERROR, False),
    }
    code, retryable = mapping[error.kind]
    return PrinterAdapterError(code, error.message, retryable=retryable, vendor_code=error.vendor_code)


def _artifact_matches(request: PrintExecutionRequest) -> bool:
    artifact = request.artifact
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
    bindings = tuple(sorted((item.material_index, item.slot_id) for item in request.material_bindings))
    return (
        request.artifact.sha256,
        request.artifact.format.value,
        plate_index,
        bindings,
        request.requested_name,
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
