# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

import asyncio
from uuid import uuid4

import pytest

from foxforge.adapters.bambu.job_control import BambuJobControlCapability
from foxforge.adapters.bambu.native import BambuNativeJobControlAction, BambuNativeJobControlResult
from foxforge.adapters.bambu.transport import BambuTransportError, BambuTransportErrorKind
from foxforge.adapters.moonraker.job_control import MoonrakerJobControlCapability
from foxforge.adapters.moonraker.native import (
    MoonrakerNativeJobControlAction,
    MoonrakerNativeJobControlResult,
)
from foxforge.domain.printers import (
    ActiveJobSnapshot,
    ConnectionState,
    JobState,
    OperationalState,
    PrinterAdapterError,
    PrinterErrorCode,
    PrinterSnapshot,
    utc_now,
)
from foxforge.domain.printers.capabilities import JobControlAction, JobControlRequest


class _BambuControlTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[BambuNativeJobControlAction, str]] = []
        self.error: BambuTransportError | None = None

    async def control_print(self, action: BambuNativeJobControlAction, expected_vendor_job_id: str):
        self.calls.append((action, expected_vendor_job_id))
        if self.error is not None:
            raise self.error
        return BambuNativeJobControlResult(accepted_at=utc_now())


class _MoonrakerControlTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[MoonrakerNativeJobControlAction, str]] = []

    async def control_print(self, action: MoonrakerNativeJobControlAction, expected_vendor_job_id: str):
        self.calls.append((action, expected_vendor_job_id))
        return MoonrakerNativeJobControlResult(accepted_at=utc_now())


def _snapshot(state: JobState = JobState.PRINTING) -> PrinterSnapshot:
    operational = OperationalState.PAUSED if state == JobState.PAUSED else OperationalState.PRINTING
    return PrinterSnapshot(
        printer_id="printer-1",
        connection=ConnectionState.CONNECTED,
        operational_state=operational,
        active_job=ActiveJobSnapshot(
            vendor_job_id="vendor-job-1",
            name="job.3mf",
            state=state,
            progress=0.2,
            elapsed_seconds=10,
            remaining_seconds=50,
            current_layer=1,
            total_layers=5,
        ),
        observed_at=utc_now(),
        stale=False,
    )


def _request(action: JobControlAction) -> JobControlRequest:
    return JobControlRequest(
        control_id=uuid4(),
        action=action,
        expected_vendor_job_id="vendor-job-1",
    )


def test_bambu_cancel_maps_to_native_stop_and_is_idempotent() -> None:
    async def scenario() -> None:
        transport = _BambuControlTransport()
        capability = BambuJobControlCapability(transport, _snapshot)  # type: ignore[arg-type]
        request = _request(JobControlAction.CANCEL)

        first = await capability.execute(request)
        second = await capability.execute(request)

        assert first == second
        assert first.vendor_job_id == "vendor-job-1"
        assert transport.calls == [(BambuNativeJobControlAction.STOP, "vendor-job-1")]

    asyncio.run(scenario())


def test_bambu_indeterminate_is_never_marked_retryable() -> None:
    async def scenario() -> None:
        transport = _BambuControlTransport()
        transport.error = BambuTransportError(BambuTransportErrorKind.INDETERMINATE, "uncertain")
        capability = BambuJobControlCapability(transport, _snapshot)  # type: ignore[arg-type]

        with pytest.raises(PrinterAdapterError) as captured:
            await capability.execute(_request(JobControlAction.PAUSE))

        assert captured.value.code == PrinterErrorCode.INDETERMINATE
        assert captured.value.retryable is False

    asyncio.run(scenario())


def test_moonraker_resume_maps_to_native_resume() -> None:
    async def scenario() -> None:
        transport = _MoonrakerControlTransport()
        capability = MoonrakerJobControlCapability(
            transport,  # type: ignore[arg-type]
            lambda: _snapshot(JobState.PAUSED),
        )
        receipt = await capability.execute(_request(JobControlAction.RESUME))

        assert receipt.action == JobControlAction.RESUME
        assert transport.calls == [(MoonrakerNativeJobControlAction.RESUME, "vendor-job-1")]

    asyncio.run(scenario())
