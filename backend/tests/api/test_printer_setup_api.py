# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1 import BearerCommandSecurity, TrustedBrowserCommandSessions, create_api_v1_app
from foxforge.application.commands import InMemoryCommandIdempotencyStore
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.printer_management import (
    PrinterConfiguration,
    PrinterConnectionValidationError,
    PrinterSetupOutcome,
)
from foxforge.application.queue import InMemoryQueueStore, QueueService
from foxforge.domain.printers import (
    ConnectionState,
    OperationalState,
    PrinterAdapterError,
    PrinterErrorCode,
    PrinterSnapshot,
)

_TOKEN = "foxforge-printer-setup-token-0123456789"
_ACCESS_CODE = "12345678"


@dataclass
class _Manager:
    saved: PrinterConfiguration | None = None
    add_error: PrinterAdapterError | None = None
    test_error: PrinterAdapterError | None = None

    def configurations(self) -> tuple[PrinterConfiguration, ...]:
        return () if self.saved is None else (self.saved,)

    def configuration(self, printer_id: str) -> PrinterConfiguration:
        assert self.saved is not None and self.saved.identity.printer_id == printer_id
        return self.saved

    async def test_connection(self, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        return _outcome(configuration, self.test_error)

    async def add(self, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        if self.add_error is not None:
            raise PrinterConnectionValidationError(self.add_error)
        self.saved = configuration
        return _outcome(configuration)

    async def update(self, printer_id: str, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        self.saved = configuration
        return _outcome(configuration)

    async def remove(self, printer_id: str) -> None:
        self.saved = None

    async def reconnect(self, printer_id: str) -> PrinterSetupOutcome:
        assert self.saved is not None
        return _outcome(self.saved)


def _outcome(
    configuration: PrinterConfiguration,
    connection_error: PrinterAdapterError | None = None,
) -> PrinterSetupOutcome:
    return PrinterSetupOutcome(
        configuration=configuration,
        snapshot=PrinterSnapshot(
            printer_id=configuration.identity.printer_id,
            connection=ConnectionState.CONNECTED if connection_error is None else ConnectionState.DISCONNECTED,
            operational_state=OperationalState.IDLE if connection_error is None else OperationalState.UNKNOWN,
            active_job=None,
            observed_at=datetime.now(UTC),
            stale=False,
        ),
        connection_error=connection_error,
    )


def _app(manager: _Manager, *, browser_sessions: bool = False):
    fleet = FleetService()
    sessions = TrustedBrowserCommandSessions(enabled=browser_sessions)
    return create_api_v1_app(
        fleet=fleet,
        queue=QueueService(fleet, InMemoryQueueStore()),
        inventory=InventoryService(InMemoryInventoryStore()),
        command_security=BearerCommandSecurity(_TOKEN, browser_sessions=sessions),
        command_idempotency=InMemoryCommandIdempotencyStore(),
        printer_management=manager,
    )


def _bambu_payload() -> dict[str, object]:
    return {
        "printerId": "x2d-main",
        "displayName": "Bambu X2D",
        "kind": "bambu",
        "model": "X2D",
        "serialNumber": "SERIAL123",
        "connection": {"host": "192.0.2.10", "accessCode": _ACCESS_CODE},
    }


def test_bambu_add_is_real_authenticated_command_and_never_echoes_access_code() -> None:
    async def scenario() -> None:
        manager = _Manager()
        client = TestClient(TestServer(_app(manager)))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/printers",
                json=_bambu_payload(),
                headers={
                    "Authorization": f"Bearer {_TOKEN}",
                    "Idempotency-Key": "printer-add-001",
                },
            )
            assert response.status == 201
            body = await response.json()
            assert body["reachable"] is True
            assert body["configuration"]["connection"] == {
                "host": "192.0.2.10",
                "accessCodeConfigured": True,
            }
            assert _ACCESS_CODE not in str(body)
            assert manager.saved is not None
            assert manager.saved.settings["access_code"] == _ACCESS_CODE
        finally:
            await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("adapter_error", "expected_code", "expected_message", "retryable"),
    [
        (
            PrinterAdapterError(
                code=PrinterErrorCode.CONNECTION_UNAVAILABLE,
                message="raw network detail that must not escape",
                retryable=True,
            ),
            "printer_connection_unavailable",
            "FoxForge could not reach the printer on the configured LAN address.",
            True,
        ),
        (
            PrinterAdapterError(
                code=PrinterErrorCode.AUTHENTICATION_FAILED,
                message="raw broker rejection that must not escape",
                retryable=False,
                vendor_code="5",
            ),
            "printer_connection_authentication_failed",
            "The printer rejected the configured LAN credentials.",
            False,
        ),
        (
            PrinterAdapterError(
                code=PrinterErrorCode.TIMEOUT,
                message="raw timeout detail that must not escape",
                retryable=True,
                vendor_code="initial_state_timeout",
            ),
            "printer_initial_state_timeout",
            "MQTT connected, but FoxForge did not receive initial state. Verify the Bambu serial number and LAN mode.",
            True,
        ),
        (
            PrinterAdapterError(
                code=PrinterErrorCode.INTERNAL_ADAPTER_ERROR,
                message="object NoneType can't be used in 'await' expression",
                retryable=False,
                vendor_code="TypeError",
            ),
            "printer_connection_internal_adapter_error",
            "The printer adapter failed while establishing the connection.",
            False,
        ),
    ],
)
def test_bambu_add_connection_failure_is_structured_sanitized_and_not_created(
    adapter_error: PrinterAdapterError,
    expected_code: str,
    expected_message: str,
    retryable: bool,
) -> None:
    async def scenario() -> None:
        manager = _Manager(add_error=adapter_error)
        client = TestClient(TestServer(_app(manager)))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/printers",
                json=_bambu_payload(),
                headers={
                    "Authorization": f"Bearer {_TOKEN}",
                    "Idempotency-Key": f"printer-add-{expected_code}",
                },
            )

            assert response.status == 422
            body = await response.json()
            assert body["error"]["code"] == expected_code
            assert body["error"]["message"] == expected_message
            assert body["error"]["retryable"] is retryable
            assert manager.saved is None
            assert _ACCESS_CODE not in str(body)
            assert adapter_error.message not in str(body)
        finally:
            await client.close()

    asyncio.run(scenario())


def test_bambu_test_connection_sanitizes_adapter_error_but_preserves_stage_code() -> None:
    async def scenario() -> None:
        manager = _Manager(
            test_error=PrinterAdapterError(
                code=PrinterErrorCode.TIMEOUT,
                message="vendor-specific raw timeout",
                retryable=True,
                vendor_code="initial_state_timeout",
            )
        )
        client = TestClient(TestServer(_app(manager)))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/printers/test-connection",
                json=_bambu_payload(),
                headers={"Authorization": f"Bearer {_TOKEN}"},
            )
            assert response.status == 200
            body = await response.json()
            assert body["reachable"] is False
            assert body["connectionError"] == {
                "code": "timeout",
                "message": (
                    "MQTT connected, but FoxForge did not receive initial state. "
                    "Verify the Bambu serial number and LAN mode."
                ),
                "retryable": True,
                "vendorCode": "initial_state_timeout",
            }
            assert "vendor-specific raw timeout" not in str(body)
            assert _ACCESS_CODE not in str(body)
        finally:
            await client.close()

    asyncio.run(scenario())


def test_moonraker_test_connection_does_not_save_configuration() -> None:
    async def scenario() -> None:
        manager = _Manager()
        client = TestClient(TestServer(_app(manager)))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/printers/test-connection",
                json={
                    "printerId": "klipper-1",
                    "displayName": "Klipper printer",
                    "kind": "moonraker",
                    "connection": {"baseUrl": "http://192.0.2.20:7125", "apiKey": "secret-key"},
                },
                headers={"Authorization": f"Bearer {_TOKEN}"},
            )
            assert response.status == 200
            body = await response.json()
            assert body["reachable"] is True
            assert body["configuration"]["connection"]["apiKeyConfigured"] is True
            assert "secret-key" not in str(body)
            assert manager.saved is None
        finally:
            await client.close()

    asyncio.run(scenario())


def test_tokenless_operator_session_bootstrap_is_rejected() -> None:
    async def scenario() -> None:
        manager = _Manager()
        client = TestClient(TestServer(_app(manager, browser_sessions=True)))
        await client.start_server()
        try:
            session_response = await client.post("/api/v1/operator-session")
            assert session_response.status == 503
            body = await session_response.json()
            assert body["error"]["code"] == "browser_session_disabled"
        finally:
            await client.close()

    asyncio.run(scenario())


def test_browser_session_can_only_be_issued_after_explicit_operator_bootstrap() -> None:
    sessions = TrustedBrowserCommandSessions(enabled=True)
    security = BearerCommandSecurity(_TOKEN, browser_sessions=sessions)

    session = security.issue_browser_session(_TOKEN)
    principal = security.authenticate(f"Bearer {session.access_token}")

    assert principal.principal_id == "operator"
