# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

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


@dataclass
class _Manager:
    saved: PrinterConfiguration | None = None
    add_error: PrinterAdapterError | None = None

    def configurations(self) -> tuple[PrinterConfiguration, ...]:
        return () if self.saved is None else (self.saved,)

    def configuration(self, printer_id: str) -> PrinterConfiguration:
        assert self.saved is not None and self.saved.identity.printer_id == printer_id
        return self.saved

    async def test_connection(self, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        return _outcome(configuration)

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


def _outcome(configuration: PrinterConfiguration) -> PrinterSetupOutcome:
    return PrinterSetupOutcome(
        configuration=configuration,
        snapshot=PrinterSnapshot(
            printer_id=configuration.identity.printer_id,
            connection=ConnectionState.CONNECTED,
            operational_state=OperationalState.IDLE,
            active_job=None,
            observed_at=datetime.now(UTC),
            stale=False,
        ),
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


def test_bambu_add_is_real_authenticated_command_and_never_echoes_access_code() -> None:
    async def scenario() -> None:
        manager = _Manager()
        client = TestClient(TestServer(_app(manager)))
        await client.start_server()
        try:
            payload = {
                "printerId": "x2d-main",
                "displayName": "Bambu X2D",
                "kind": "bambu",
                "model": "X2D",
                "serialNumber": "SERIAL123",
                "connection": {"host": "192.0.2.10", "accessCode": "12345678"},
            }
            response = await client.post(
                "/api/v1/printers",
                json=payload,
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
            assert "12345678" not in str(body)
            assert manager.saved is not None
            assert manager.saved.settings["access_code"] == "12345678"
        finally:
            await client.close()

    asyncio.run(scenario())


def test_bambu_add_connection_failure_is_not_reported_as_created() -> None:
    async def scenario() -> None:
        manager = _Manager(
            add_error=PrinterAdapterError(
                code=PrinterErrorCode.CONNECTION_UNAVAILABLE,
                message="Bambu printer is unreachable from the FoxForge server.",
                retryable=True,
            )
        )
        client = TestClient(TestServer(_app(manager)))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/printers",
                json={
                    "printerId": "x2d-main",
                    "displayName": "Bambu X2D",
                    "kind": "bambu",
                    "model": "X2D",
                    "serialNumber": "SERIAL123",
                    "connection": {"host": "192.0.2.10", "accessCode": "12345678"},
                },
                headers={
                    "Authorization": f"Bearer {_TOKEN}",
                    "Idempotency-Key": "printer-add-unreachable-001",
                },
            )

            assert response.status == 400
            body = await response.json()
            assert body["error"]["code"] == "invalid_request"
            assert body["error"]["message"] == "Bambu printer is unreachable from the FoxForge server."
            assert body["error"]["retryable"] is False
            assert manager.saved is None
            assert "12345678" not in str(body)
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
