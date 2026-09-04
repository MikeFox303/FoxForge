# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import replace
from pathlib import Path

from foxforge.application.events import ApplicationEventJournal, ApplicationEventTopic
from foxforge.application.fleet import FleetService
from foxforge.application.printer_management import (
    PrinterConfiguration,
    PrinterConfigurationConflictError,
    PrinterConfigurationNotFoundError,
    PrinterSetupOutcome,
)
from foxforge.application.secrets import SecretStore
from foxforge.domain.printers import PrinterAdapterError
from foxforge.infrastructure.printers import AdapterRegistry

from .config import PrinterRuntimeConfig, RuntimeConfig, save_runtime_config
from .secret_settings import (
    delete_printer_secrets,
    hydrate_settings,
    persist_secret_settings,
    secret_fields,
    secret_key,
)


class RuntimePrinterManager:
    """Persist printer setup and apply it to the live FleetService.

    Non-secret composition remains in the private runtime config. Credential
    values cross a SecretStore port and are hydrated only when an adapter or
    internal configuration view needs them.
    """

    def __init__(
        self,
        *,
        fleet: FleetService,
        registry: AdapterRegistry,
        config_path: Path,
        config: RuntimeConfig,
        secret_store: SecretStore,
        events: ApplicationEventJournal | None = None,
    ) -> None:
        self._fleet = fleet
        self._registry = registry
        self._config_path = config_path
        self._config = config
        self._secret_store = secret_store
        self._events = events
        self._lock = asyncio.Lock()

    def configurations(self) -> tuple[PrinterConfiguration, ...]:
        return tuple(_application_configuration(printer, self._secret_store) for printer in self._config.printers)

    def configuration(self, printer_id: str) -> PrinterConfiguration:
        runtime = self._find(printer_id)
        if runtime is None:
            raise PrinterConfigurationNotFoundError(printer_id)
        return _application_configuration(runtime, self._secret_store)

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
            try:
                runtime = _runtime_configuration(configuration, self._secret_store)
                updated = replace(previous, printers=(*previous.printers, runtime))
                save_runtime_config(self._config_path, updated)
            except Exception:
                delete_printer_secrets(configuration.identity, self._secret_store)
                raise
            try:
                await self._fleet.add_adapter(adapter)
            except Exception:
                save_runtime_config(self._config_path, previous)
                delete_printer_secrets(configuration.identity, self._secret_store)
                raise
            self._config = updated
            self._publish_configuration_change(printer_id, "printer_added")

        return await self._connect(configuration)

    async def update(self, printer_id: str, configuration: PrinterConfiguration) -> PrinterSetupOutcome:
        if configuration.identity.printer_id != printer_id:
            raise ValueError("printerId in the request must match the route")

        async with self._lock:
            existing = self._find(printer_id)
            if existing is None:
                raise PrinterConfigurationNotFoundError(printer_id)

            effective = _with_existing_secrets(configuration, existing, self._secret_store)
            replacement = self._registry.create(effective.identity, effective.settings)
            previous = self._config
            secret_backup = _secret_values(existing.identity, self._secret_store)
            try:
                updated_printers = tuple(
                    _runtime_configuration(effective, self._secret_store)
                    if item.identity.printer_id == printer_id
                    else item
                    for item in previous.printers
                )
                updated = replace(previous, printers=updated_printers)
                save_runtime_config(self._config_path, updated)
            except Exception:
                _restore_secret_values(existing.identity, secret_backup, self._secret_store)
                raise

            with suppress(PrinterAdapterError):
                await self._fleet.remove_adapter(printer_id)
            try:
                await self._fleet.add_adapter(replacement)
            except Exception:
                save_runtime_config(self._config_path, previous)
                _restore_secret_values(existing.identity, secret_backup, self._secret_store)
                old_adapter = self._registry.create(
                    existing.identity,
                    hydrate_settings(existing.identity, existing.settings, self._secret_store),
                )
                await self._fleet.add_adapter(old_adapter)
                with suppress(PrinterAdapterError):
                    await self._fleet.connect(printer_id)
                raise
            self._config = updated
            self._publish_configuration_change(printer_id, "printer_updated")

        return await self._connect(effective)

    async def remove(self, printer_id: str) -> None:
        async with self._lock:
            existing = self._find(printer_id)
            if existing is None:
                raise PrinterConfigurationNotFoundError(printer_id)
            previous = self._config
            updated = replace(
                previous,
                printers=tuple(item for item in previous.printers if item.identity.printer_id != printer_id),
            )
            save_runtime_config(self._config_path, updated)
            try:
                delete_printer_secrets(existing.identity, self._secret_store)
            except Exception:
                save_runtime_config(self._config_path, previous)
                raise
            self._config = updated
            with suppress(PrinterAdapterError):
                await self._fleet.remove_adapter(printer_id)
            self._publish_configuration_change(printer_id, "printer_removed")

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

    def _publish_configuration_change(self, printer_id: str, change: str) -> None:
        if self._events is None:
            return
        self._events.publish(
            ApplicationEventTopic.PRINTER_CONFIGURATION,
            change,
            resource_id=printer_id,
        )


def _application_configuration(runtime: PrinterRuntimeConfig, store: SecretStore) -> PrinterConfiguration:
    return PrinterConfiguration(
        identity=runtime.identity,
        settings=hydrate_settings(runtime.identity, runtime.settings, store),
    )


def _runtime_configuration(configuration: PrinterConfiguration, store: SecretStore) -> PrinterRuntimeConfig:
    return PrinterRuntimeConfig(
        identity=configuration.identity,
        settings=persist_secret_settings(configuration.identity, configuration.settings, store),
    )


def _with_existing_secrets(
    configuration: PrinterConfiguration,
    existing: PrinterRuntimeConfig,
    store: SecretStore,
) -> PrinterConfiguration:
    settings = dict(configuration.settings)
    existing_settings = hydrate_settings(existing.identity, existing.settings, store)
    for field_name in secret_fields(configuration.identity):
        if field_name not in settings and field_name in existing_settings:
            settings[field_name] = existing_settings[field_name]
    return PrinterConfiguration(identity=configuration.identity, settings=settings)


def _secret_values(identity, store: SecretStore) -> dict[str, str | None]:
    return {field_name: store.get(secret_key(identity, field_name)) for field_name in secret_fields(identity)}


def _restore_secret_values(identity, values: dict[str, str | None], store: SecretStore) -> None:
    for field_name, value in values.items():
        key = secret_key(identity, field_name)
        if value is None:
            store.delete(key)
        else:
            store.set(key, value)
