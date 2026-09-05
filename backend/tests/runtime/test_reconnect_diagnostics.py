# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from foxforge.domain.printers import (
    ConnectionState,
    OperationalState,
    PrinterAdapterError,
    PrinterErrorCode,
    PrinterSnapshot,
)
from foxforge.runtime.reconnect import ReconnectDiagnostics, ReconnectPolicy, run_connection_supervisor


class _FailThenRecoverFleet:
    def __init__(self) -> None:
        self.state = ConnectionState.DISCONNECTED
        self.attempts = 0
        self.connected = asyncio.Event()

    @property
    def printer_ids(self) -> tuple[str, ...]:
        return ("x2d-main",)

    def snapshot(self, printer_id: str) -> PrinterSnapshot:
        assert printer_id == "x2d-main"
        return PrinterSnapshot(
            printer_id=printer_id,
            connection=self.state,
            operational_state=(
                OperationalState.IDLE if self.state == ConnectionState.CONNECTED else OperationalState.OFFLINE
            ),
            active_job=None,
            observed_at=datetime.now(UTC),
            stale=self.state != ConnectionState.CONNECTED,
        )

    async def connect(self, printer_id: str) -> None:
        assert printer_id == "x2d-main"
        self.attempts += 1
        if self.attempts == 1:
            raise PrinterAdapterError(
                code=PrinterErrorCode.AUTHENTICATION_FAILED,
                message="raw access code rejected by broker",
                retryable=False,
                vendor_code="5",
            )
        self.state = ConnectionState.CONNECTED
        self.connected.set()


def _policy() -> ReconnectPolicy:
    return ReconnectPolicy(
        base_delay_seconds=0.005,
        max_delay_seconds=0.01,
        jitter_ratio=0,
        discovery_interval_seconds=0.002,
    )


def test_registry_keeps_only_normalized_reconnect_context() -> None:
    diagnostics = ReconnectDiagnostics()
    diagnostics.record_attempt("x2d-main")
    diagnostics.record_failure(
        "x2d-main",
        consecutive_failures=2,
        error_code=PrinterErrorCode.AUTHENTICATION_FAILED,
        retryable=False,
        retry_delay_seconds=15,
    )

    status = diagnostics.statuses()[0]
    assert status.printer_id == "x2d-main"
    assert status.consecutive_failures == 2
    assert status.last_error_code == PrinterErrorCode.AUTHENTICATION_FAILED
    assert status.last_error_retryable is False
    assert status.last_attempt_at is not None
    assert status.last_failure_at is not None
    assert status.next_retry_at is not None
    assert not hasattr(status, "message")
    assert not hasattr(status, "vendor_code")


def test_supervisor_retains_last_failure_context_after_recovery() -> None:
    async def scenario() -> None:
        fleet = _FailThenRecoverFleet()
        diagnostics = ReconnectDiagnostics()
        supervisor = asyncio.create_task(
            run_connection_supervisor(
                fleet,
                _policy(),
                random_value=lambda: 0.5,
                diagnostics=diagnostics,
            )
        )
        try:
            await asyncio.wait_for(fleet.connected.wait(), timeout=0.2)
            for _ in range(20):
                status = diagnostics.statuses()[0]
                if status.recovered_at is not None:
                    break
                await asyncio.sleep(0.002)

            status = diagnostics.statuses()[0]
            assert fleet.attempts == 2
            assert status.consecutive_failures == 0
            assert status.last_error_code == PrinterErrorCode.AUTHENTICATION_FAILED
            assert status.last_error_retryable is False
            assert status.last_failure_at is not None
            assert status.recovered_at is not None
            assert status.next_retry_at is None
        finally:
            supervisor.cancel()
            await asyncio.gather(supervisor, return_exceptions=True)

    asyncio.run(scenario())


def test_registry_drops_removed_printers() -> None:
    diagnostics = ReconnectDiagnostics()
    diagnostics.record_attempt("old-printer")
    diagnostics.record_attempt("active-printer")

    diagnostics.retain({"active-printer"})

    assert [status.printer_id for status in diagnostics.statuses()] == ["active-printer"]
