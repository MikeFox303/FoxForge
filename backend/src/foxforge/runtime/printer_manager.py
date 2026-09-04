# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import replace
from pathlib import Path

from foxforge.application.fleet import FleetService
from foxforge.application.printer_management import (
    PrinterConfiguration,
    PrinterConfigurationConflictError,
    PrinterConfigurationNotFoundError,
    PrinterSetupOutcome,
)
from foxforge.domain.printers import PrinterAdapterError
from foxforge.infrastructure.printers import AdapterRegistry

from .config import PrinterRuntimeConfig, RuntimeConfig, save_runtime_config


class RuntimePrinterManager:
    """Persist printer setup and apply it to the live FleetService.

    The JSON file remains a private deployment artifact for restart durability;
    it is no longer the user-facing configuration interface. All mutations are
    serialized so the persisted set and live fleet cannot race inside the
    single-process FoxForge runtime.
    """

    def __init__(
        self,
        *,
        fleet: FleetService,
        registry: AdapterRegistry,
        config_path: Path,
        config: RuntimeConfig,
    ) -> None:
        self._fleet = fleet
        self._registry = registry
        self._config_path = config_path
        self._config = config
        self._lock = asyncio.Lock()

    def configurations(self) -> tuple[PrinterConfiguration, ...]:
        return tuple(_application_configuration(printer) for printer in self._config.printers)

    def configuration(self, printer_id: str) -> PrinterConfiguration:
        runtime = self._find(printer_id)
        if runtime is None:
            raise PrinterConfigurationNotFoundError(printer_id)
        return _application_configuration(runtime)

    async def test_connection(self, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        adapter = self._registry.create(configuration.identity, configuration.settings)
        connection_error: PrinterAdapterError | None = None
        try:
            await adapter.connect()
        except PrinterAdapterError as error:
            connection_error = error
        snapshot = adapter.snapshot()
        with suppress(PrinterAdapterError):
            await adapter.disconnect()
        return PrinterSetupOutcome(
            configuration=configuration,
            snapshot=snapshot,
            connection_error=connection_error,
        )

    async def add(self, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        async with self._lock:
            printer_id = configuration.identity.printer_id
            if self._find(printer_id) is not None:
                raise PrinterConfigurationConflictError(f"printer is already configured: {printer_id}")

            adapter = self._registry.create(configuration.identity, configuration.settings)
            previous = self._config
            runtime = _runtime_configuration(configuration)
            updated = replace(previous, printers=(*previous.printers, runtime))
            save_runtime_config(self._config_path, updated)
            try:
                await self._fleet.add_adapter(adapter)
            except Exception:
                save_runtime_config(self._config_path, previous)
                raise
            self._config = updated

        return await self._connect(configuration)

    async def update(self, printer_id: str, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        if configuration.identity.printer_id != printer_id:
            raise ValueError("printerId in the request must match the route")

        async with self._lock:
            existing = self._find(printer_id)
            if existing is None:
                raise PrinterConfigurationNotFoundError(printer_id)

            replacement = self._registry.create(configuration.identity, configuration.settings)
            previous = self._config
            updated_printers = tuple(
                _runtime_configuration(configuration) if item.identity.printer_id == printer_id else item
                for item in previous.printers
            )
            updated = replace(previous, printers=updated_printers)
            save_runtime_config(self._config_path, updated)

            with suppress(PrinterAdapterError):
                await self._fleet.remove_adapter(printer_id)
            try:
                await self._fleet.add_adapter(replacement)
            except Exception:
                save_runtime_config(self._config_path, previous)
                old_adapter = self._registry.create(existing.identity, existing.settings)
                await self._fleet.add_adapter(old_adapter)
                with suppress(PrinterAdapterError):
                    await self._fleet.connect(printer_id)
                raise
            self._config = updated

        return await self._connect(configuration)

    async def remove(self, printer_id: str) -> None:
        async with self._lock:
            if self._find(printer_id) is None:
                raise PrinterConfigurationNotFoundError(printer_id)
            updated = replace(
                self._config,
                printers=tuple(item for item in self._config.printers if item.identity.printer_id != printer_id),
            )
            save_runtime_config(self._config_path, updated)
            self._config = updated
            with suppress(PrinterAdapterError):
                await self._fleet.remove_adapter(printer_id)

    async def reconnect(self, printer_id: str) -> PrinterSetupOutcome:
        configuration = self.configuration(printer_id)
        return await self._connect(configuration)

    def _find(self, printer_id: str) -> PrinterRuntimeConfig | None:
        return next(
            (item for item in self._config.printers if item.identity.printer_id == printer_id),
            None,
        )

    async def _connect(self, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        printer_id = configuration.identity.printer_id
        connection_error: PrinterAdapterError | None = None
        try:
            await self._fleet.connect(printer_id)
        except PrinterAdapterError as error:
            connection_error = error
        return PrinterSetupOutcome(
            configuration=configuration,
            snapshot=self._fleet.snapshot(printer_id),
            connection_error=connection_error,
        )


def _application_configuration(runtime: PrinterRuntimeConfig) -> PrinterConfiguration:
    return PrinterConfiguration(identity=runtime.identity, settings=dict(runtime.settings))


def _runtime_configuration(configuration: PrinterConfiguration) -> PrinterRuntimeConfig:
    return PrinterRuntimeConfig(identity=configuration.identity, settings=dict(configuration.settings))
