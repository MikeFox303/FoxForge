# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from foxforge.domain.printers import (
    ConnectionState,
    OperationalState,
    PrinterAdapterError,
    PrinterErrorCode,
    PrinterSnapshot,
)
from foxforge.runtime.reconnect import ReconnectDiagnostics, ReconnectPolicy, run_connection_supervisor
from foxforge.runtime.reconnect_routes import register_reconnect_diagnostic_routes


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
                message="synthetic broker authentication failure",
                retryable=False,
                vendor_code="synthetic-code",
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


def test_disconnect_event_context_is_normalized_and_redacted() -> None:
    diagnostics = ReconnectDiagnostics()
    diagnostics.record_disconnect_error(
        "x2d-main",
        PrinterAdapterError(
            code=PrinterErrorCode.UNAVAILABLE,
            message="raw transport detail that must stay private",
            retryable=True,
            vendor_code="raw-vendor-detail",
        ),
    )

    status = diagnostics.statuses()[0]
    assert status.consecutive_failures == 0
    assert status.last_error_code == PrinterErrorCode.UNAVAILABLE
    assert status.last_error_retryable is True
    assert status.last_failure_at is not None
    assert status.next_retry_at is None
    assert status.recovered_at is None
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


def test_reconnect_diagnostics_route_exposes_only_normalized_fields() -> None:
    async def scenario() -> None:
        diagnostics = ReconnectDiagnostics()
        diagnostics.record_disconnect_error(
            "x2d-main",
            PrinterAdapterError(
                code=PrinterErrorCode.AUTHENTICATION_FAILED,
                message="private-transport-detail",
                retryable=False,
                vendor_code="private-vendor-detail",
            ),
        )
        app = web.Application()
        register_reconnect_diagnostic_routes(app, diagnostics)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/api/v1/diagnostics/reconnect")
            assert response.status == 200
            body = await response.json()
            assert body["apiVersion"] == "1"
            assert len(body["printers"]) == 1
            printer = body["printers"][0]
            assert printer["printerId"] == "x2d-main"
            assert printer["lastErrorCode"] == "authentication_failed"
            assert printer["lastErrorRetryable"] is False
            assert "message" not in printer
            assert "vendorCode" not in printer
            serialized = str(body)
            assert "private-transport-detail" not in serialized
            assert "private-vendor-detail" not in serialized
        finally:
            await client.close()

    asyncio.run(scenario())


def test_registry_drops_removed_printers() -> None:
    diagnostics = ReconnectDiagnostics()
    diagnostics.record_attempt("old-printer")
    diagnostics.record_attempt("active-printer")

    diagnostics.retain({"active-printer"})

    assert [status.printer_id for status in diagnostics.statuses()] == ["active-printer"]
