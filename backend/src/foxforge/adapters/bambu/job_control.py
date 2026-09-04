# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from foxforge.domain.printers import PrinterAdapterError, PrinterErrorCode, PrinterSnapshot
from foxforge.domain.printers.capabilities import (
    JOB_CONTROL_CAPABILITY_ID,
    JOB_CONTROL_MAJOR_VERSION,
    JobControlAction,
    JobControlAssessment,
    JobControlDescriptor,
    JobControlReceipt,
    JobControlRequest,
    assess_job_control,
)

from .native import BambuNativeJobControlAction
from .print_execution import normalize_bambu_transport_error
from .transport import BambuTransport, BambuTransportError

_ACTIONS = {
    JobControlAction.PAUSE: BambuNativeJobControlAction.PAUSE,
    JobControlAction.RESUME: BambuNativeJobControlAction.RESUME,
    JobControlAction.CANCEL: BambuNativeJobControlAction.STOP,
}


class BambuJobControlCapability:
    """Guard common pause/resume/cancel before translating to Bambu LAN commands."""

    def __init__(self, transport: BambuTransport, printer_snapshot: Callable[[], PrinterSnapshot]) -> None:
        self._transport = transport
        self._printer_snapshot = printer_snapshot
        self._descriptor = JobControlDescriptor(
            capability_id=JOB_CONTROL_CAPABILITY_ID,
            major_version=JOB_CONTROL_MAJOR_VERSION,
            supported_actions=frozenset(_ACTIONS),
            requires_vendor_job_identity=True,
        )
        self._confirmed: dict[UUID, tuple[tuple[str, str], JobControlReceipt]] = {}

    @property
    def descriptor(self) -> JobControlDescriptor:
        return self._descriptor

    async def assess(self, request: JobControlRequest) -> JobControlAssessment:
        return assess_job_control(self._printer_snapshot(), self._descriptor, request)

    async def execute(self, request: JobControlRequest) -> JobControlReceipt:
        fingerprint = (request.action.value, str(request.expected_vendor_job_id))
        previous = self._confirmed.get(request.control_id)
        if previous is not None:
            previous_fingerprint, receipt = previous
            if previous_fingerprint != fingerprint:
                raise PrinterAdapterError(
                    PrinterErrorCode.CONFLICT,
                    "control_id was reused with a materially different job-control request",
                    retryable=False,
                )
            return receipt

        assessment = await self.assess(request)
        if not assessment.eligible:
            blocker = assessment.blockers[0]
            code = {
                "offline": PrinterErrorCode.CONNECTION_UNAVAILABLE,
                "stale": PrinterErrorCode.NOT_READY,
                "no_active_job": PrinterErrorCode.NOT_READY,
                "job_identity_unavailable": PrinterErrorCode.NOT_READY,
                "job_mismatch": PrinterErrorCode.CONFLICT,
                "invalid_state": PrinterErrorCode.NOT_READY,
                "unsupported_action": PrinterErrorCode.UNSUPPORTED,
            }[blocker.code.value]
            raise PrinterAdapterError(
                code,
                blocker.message or blocker.code.value,
                retryable=blocker.code.value in {"offline", "stale", "no_active_job", "invalid_state"},
            )

        try:
            result = await self._transport.control_print(
                _ACTIONS[request.action],
                str(request.expected_vendor_job_id),
            )
        except BambuTransportError as error:
            raise normalize_bambu_transport_error(error) from error

        receipt = JobControlReceipt(
            control_id=request.control_id,
            action=request.action,
            accepted_at=result.accepted_at,
            vendor_job_id=request.expected_vendor_job_id,
        )
        self._confirmed[request.control_id] = (fingerprint, receipt)
        return receipt
