# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1 import BearerCommandSecurity, create_api_v1_app
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
    PrinterIdentity,
    PrinterSnapshot,
)

_TOKEN = "foxforge-printer-idempotency-token-0123456789"
_ACCESS_CODE = "12345678"


@dataclass
class _Manager:
    saved: PrinterConfiguration | None = None
    add_error: PrinterAdapterError | None = None
    update_error: PrinterAdapterError | None = None
    add_calls: int = 0
    update_calls: int = 0

    def configurations(self) -> tuple[PrinterConfiguration, ...]:
        return () if self.saved is None else (self.saved,)

    def configuration(self, printer_id: str) -> PrinterConfiguration:
        if self.saved is None or self.saved.identity.printer_id != printer_id:
            from foxforge.application.printer_management import PrinterConfigurationNotFoundError

            raise PrinterConfigurationNotFoundError(printer_id)
        return self.saved

    async def test_connection(self, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        return _outcome(configuration)

    async def add(self, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        self.add_calls += 1
        if self.add_error is not None:
            raise PrinterConnectionValidationError(self.add_error)
        self.saved = configuration
        return _outcome(configuration)

    async def update(self, printer_id: str, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        self.update_calls += 1
        if self.update_error is not None:
            raise PrinterConnectionValidationError(self.update_error)
        self.saved = configuration
        return _outcome(configuration)

    async def remove(self, printer_id: str) -> None:
        self.saved = None

    async def reconnect(self, printer_id: str) -> PrinterSetupOutcome:
        assert self.saved is not None
        return _outcome(self.saved)


def _configuration(*, access_code: str = _ACCESS_CODE) -> PrinterConfiguration:
    return PrinterConfiguration(
        identity=PrinterIdentity(
            printer_id="x2d-main",
            display_name="Bambu X2D",
            vendor="bambu_lab",
            model="X2D",
            serial_number="SERIAL123",
            adapter_kind="bambu",
        ),
        settings={"host": "192.0.2.10", "access_code": access_code},
    )


def _payload(*, access_code: str = _ACCESS_CODE) -> dict[str, object]:
    return {
        "printerId": "x2d-main",
        "displayName": "Bambu X2D",
        "kind": "bambu",
        "model": "X2D",
        "serialNumber": "SERIAL123",
        "connection": {"host": "192.0.2.10", "accessCode": access_code},
    }


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
        connection_error=None,
    )


def _app(manager: _Manager):
    fleet = FleetService()
    return create_api_v1_app(
        fleet=fleet,
        queue=QueueService(fleet, InMemoryQueueStore()),
        inventory=InventoryService(InMemoryInventoryStore()),
        command_security=BearerCommandSecurity(_TOKEN),
        command_idempotency=InMemoryCommandIdempotencyStore(),
        printer_management=manager,
    )


def _headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_TOKEN}",
        "Idempotency-Key": key,
    }


def test_failed_add_is_terminal_and_replays_without_reexecuting_manager() -> None:
    async def scenario() -> None:
        raw_message = "private broker detail"
        manager = _Manager(
            add_error=PrinterAdapterError(
                code=PrinterErrorCode.AUTHENTICATION_FAILED,
                message=raw_message,
                retryable=False,
                vendor_code="5",
            )
        )
        client = TestClient(TestServer(_app(manager)))
        await client.start_server()
        try:
            first = await client.post(
                "/api/v1/printers",
                json=_payload(),
                headers=_headers("failed-add-001"),
            )
            second = await client.post(
                "/api/v1/printers",
                json=_payload(),
                headers=_headers("failed-add-001"),
            )

            assert first.status == 422
            assert second.status == 422
            first_body = await first.json()
            second_body = await second.json()
            assert first_body["error"]["code"] == "printer_connection_authentication_failed"
            assert second_body["error"]["code"] == first_body["error"]["code"]
            assert second_body["error"]["message"] == first_body["error"]["message"]
            assert second_body["error"]["retryable"] is False
            assert manager.add_calls == 1
            assert manager.saved is None
            assert raw_message not in str(first_body)
            assert raw_message not in str(second_body)
            assert _ACCESS_CODE not in str(first_body)
            assert _ACCESS_CODE not in str(second_body)
        finally:
            await client.close()

    asyncio.run(scenario())


def test_failed_update_is_terminal_replays_and_keeps_previous_configuration() -> None:
    async def scenario() -> None:
        previous = _configuration(access_code="OLD-CODE")
        raw_message = "private timeout from transport"
        manager = _Manager(
            saved=previous,
            update_error=PrinterAdapterError(
                code=PrinterErrorCode.TIMEOUT,
                message=raw_message,
                retryable=True,
                vendor_code="initial_state_timeout",
            ),
        )
        client = TestClient(TestServer(_app(manager)))
        await client.start_server()
        try:
            first = await client.put(
                "/api/v1/printers/x2d-main",
                json=_payload(),
                headers=_headers("failed-update-001"),
            )
            second = await client.put(
                "/api/v1/printers/x2d-main",
                json=_payload(),
                headers=_headers("failed-update-001"),
            )

            assert first.status == 422
            assert second.status == 422
            first_body = await first.json()
            second_body = await second.json()
            assert first_body["error"]["code"] == "printer_initial_state_timeout"
            assert second_body["error"]["code"] == first_body["error"]["code"]
            assert second_body["error"]["message"] == first_body["error"]["message"]
            assert second_body["error"]["retryable"] is True
            assert manager.update_calls == 1
            assert manager.saved == previous
            assert raw_message not in str(first_body)
            assert raw_message not in str(second_body)
            assert _ACCESS_CODE not in str(first_body)
            assert _ACCESS_CODE not in str(second_body)
        finally:
            await client.close()

    asyncio.run(scenario())
