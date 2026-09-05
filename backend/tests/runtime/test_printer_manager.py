# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

import pytest

from foxforge.application.events import ApplicationEventJournal, ApplicationEventTopic, ApplicationStreamItemKind
from foxforge.application.fleet import FleetService
from foxforge.application.printer_management import PrinterConfiguration, PrinterConnectionValidationError
from foxforge.application.secrets import InMemorySecretStore
from foxforge.domain.printers import ConnectionState, PrinterAdapterError, PrinterErrorCode, PrinterIdentity
from foxforge.infrastructure.printers import AdapterRegistry
from foxforge.runtime.config import CONFIG_SCHEMA_VERSION, RuntimeConfig, load_runtime_config
from foxforge.runtime.printer_manager import RuntimePrinterManager
from foxforge.testing import FakePrinterAdapter


class _UnavailablePrinterAdapter(FakePrinterAdapter):
    async def connect(self) -> None:
        raise PrinterAdapterError(
            code=PrinterErrorCode.CONNECTION_UNAVAILABLE,
            message="printer is unreachable",
            retryable=True,
        )


class _BrokenPrinterAdapter(FakePrinterAdapter):
    async def connect(self) -> None:
        raise TypeError("object NoneType can't be used in 'await' expression")


def _configuration(printer_id: str = "printer-ui", *, adapter_kind: str = "fake-ui") -> PrinterConfiguration:
    return PrinterConfiguration(
        identity=PrinterIdentity(
            printer_id=printer_id,
            display_name="UI configured printer",
            vendor="test",
            model="Test",
            serial_number=None,
            adapter_kind=adapter_kind,
        ),
        settings={"endpoint": "local"},
    )


def _empty_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(schema_version=CONFIG_SCHEMA_VERSION, printers=())


def test_add_persists_and_joins_live_fleet_without_restart(tmp_path) -> None:
    async def scenario() -> None:
        config_path = tmp_path / "config.json"
        fleet = FleetService()
        registry = AdapterRegistry()
        registry.register("fake-ui", lambda identity, settings: FakePrinterAdapter(identity))
        manager = RuntimePrinterManager(
            fleet=fleet,
            registry=registry,
            config_path=config_path,
            config=_empty_runtime_config(),
            secret_store=InMemorySecretStore(),
        )
        try:
            outcome = await manager.add(_configuration())

            assert outcome.connection_error is None
            assert outcome.snapshot.connection == ConnectionState.CONNECTED
            assert fleet.printer_ids == ("printer-ui",)
            assert load_runtime_config(config_path).printers[0].identity.printer_id == "printer-ui"
        finally:
            await fleet.aclose()

    asyncio.run(scenario())


def test_add_does_not_persist_or_join_fleet_when_preflight_fails(tmp_path) -> None:
    async def scenario() -> None:
        config_path = tmp_path / "config.json"
        fleet = FleetService()
        registry = AdapterRegistry()
        registry.register("fake-unavailable", lambda identity, settings: _UnavailablePrinterAdapter(identity))
        manager = RuntimePrinterManager(
            fleet=fleet,
            registry=registry,
            config_path=config_path,
            config=_empty_runtime_config(),
            secret_store=InMemorySecretStore(),
        )
        try:
            with pytest.raises(PrinterConnectionValidationError) as captured:
                await manager.add(_configuration(adapter_kind="fake-unavailable"))

            assert captured.value.error.code == PrinterErrorCode.CONNECTION_UNAVAILABLE
            assert captured.value.error.retryable is True
            assert fleet.printer_ids == ()
            assert manager.configurations() == ()
            assert not config_path.exists()
        finally:
            await fleet.aclose()

    asyncio.run(scenario())


def test_test_connection_normalizes_unexpected_runtime_errors(tmp_path) -> None:
    async def scenario() -> None:
        config_path = tmp_path / "config.json"
        fleet = FleetService()
        registry = AdapterRegistry()
        registry.register("fake-broken", lambda identity, settings: _BrokenPrinterAdapter(identity))
        manager = RuntimePrinterManager(
            fleet=fleet,
            registry=registry,
            config_path=config_path,
            config=_empty_runtime_config(),
            secret_store=InMemorySecretStore(),
        )
        try:
            outcome = await manager.test_connection(_configuration(adapter_kind="fake-broken"))

            assert outcome.connection_error is not None
            assert outcome.connection_error.code == PrinterErrorCode.INTERNAL_ADAPTER_ERROR
            assert outcome.connection_error.message == "Printer adapter failed while establishing the connection."
            assert outcome.connection_error.vendor_code == "TypeError"
            assert "NoneType" not in outcome.connection_error.message
            assert fleet.printer_ids == ()
            assert not config_path.exists()
        finally:
            await fleet.aclose()

    asyncio.run(scenario())


def test_test_connection_does_not_persist_or_join_fleet(tmp_path) -> None:
    async def scenario() -> None:
        config_path = tmp_path / "config.json"
        fleet = FleetService()
        registry = AdapterRegistry()
        registry.register("fake-ui", lambda identity, settings: FakePrinterAdapter(identity))
        manager = RuntimePrinterManager(
            fleet=fleet,
            registry=registry,
            config_path=config_path,
            config=_empty_runtime_config(),
            secret_store=InMemorySecretStore(),
        )
        try:
            outcome = await manager.test_connection(_configuration())
            assert outcome.snapshot.connection == ConnectionState.CONNECTED
            assert fleet.printer_ids == ()
            assert not config_path.exists()
        finally:
            await fleet.aclose()

    asyncio.run(scenario())


def test_remove_updates_persistence_and_live_fleet(tmp_path) -> None:
    async def scenario() -> None:
        config_path = tmp_path / "config.json"
        fleet = FleetService()
        registry = AdapterRegistry()
        registry.register("fake-ui", lambda identity, settings: FakePrinterAdapter(identity))
        manager = RuntimePrinterManager(
            fleet=fleet,
            registry=registry,
            config_path=config_path,
            config=_empty_runtime_config(),
            secret_store=InMemorySecretStore(),
        )
        try:
            await manager.add(_configuration())
            await manager.remove("printer-ui")
            assert fleet.printer_ids == ()
            assert load_runtime_config(config_path).printers == ()
        finally:
            await fleet.aclose()

    asyncio.run(scenario())


def test_configuration_mutations_publish_p2_events_but_test_connection_does_not(tmp_path) -> None:
    async def scenario() -> None:
        config_path = tmp_path / "config.json"
        fleet = FleetService()
        registry = AdapterRegistry()
        registry.register("fake-ui", lambda identity, settings: FakePrinterAdapter(identity))
        journal = ApplicationEventJournal()
        manager = RuntimePrinterManager(
            fleet=fleet,
            registry=registry,
            config_path=config_path,
            config=_empty_runtime_config(),
            secret_store=InMemorySecretStore(),
            events=journal,
        )
        stream = journal.subscribe()
        try:
            assert (await anext(stream)).kind == ApplicationStreamItemKind.RESYNC_REQUIRED

            await manager.test_connection(_configuration())
            assert journal.sequence == 0

            await manager.add(_configuration())
            added = await anext(stream)
            assert added.topic == ApplicationEventTopic.PRINTER_CONFIGURATION
            assert added.change == "printer_added"
            assert added.resource_id == "printer-ui"

            updated_configuration = PrinterConfiguration(
                identity=_configuration().identity,
                settings={"endpoint": "updated"},
            )
            await manager.update("printer-ui", updated_configuration)
            updated = await anext(stream)
            assert updated.topic == ApplicationEventTopic.PRINTER_CONFIGURATION
            assert updated.change == "printer_updated"

            await manager.remove("printer-ui")
            removed = await anext(stream)
            assert removed.topic == ApplicationEventTopic.PRINTER_CONFIGURATION
            assert removed.change == "printer_removed"
            assert journal.sequence == 3
        finally:
            await stream.aclose()  # type: ignore[attr-defined]
            await fleet.aclose()

    asyncio.run(scenario())
