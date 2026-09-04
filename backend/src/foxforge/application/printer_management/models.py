# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from foxforge.domain.printers import PrinterAdapterError, PrinterIdentity, PrinterSnapshot


@dataclass(frozen=True, slots=True)
class PrinterConfiguration:
    """Persisted composition data for one printer.

    Settings remain an opaque JSON-compatible mapping at this boundary. Vendor
    factories own their interpretation; common application code never inspects
    Bambu or Moonraker credential fields.
    """

    identity: PrinterIdentity
    settings: dict[str, object]


@dataclass(frozen=True, slots=True)
class PrinterSetupOutcome:
    configuration: PrinterConfiguration
    snapshot: PrinterSnapshot
    connection_error: PrinterAdapterError | None = None


class PrinterConfigurationNotFoundError(KeyError):
    def __init__(self, printer_id: str) -> None:
        self.printer_id = printer_id
        super().__init__(printer_id)


class PrinterConfigurationConflictError(RuntimeError):
    pass


class PrinterManagementService(Protocol):
    def configurations(self) -> tuple[PrinterConfiguration, ...]: ...

    def configuration(self, printer_id: str) -> PrinterConfiguration: ...

    async def test_connection(self, configuration: PrinterConfiguration) -> PrinterSetupOutcome: ...

    async def add(self, configuration: PrinterConfiguration) -> PrinterSetupOutcome: ...

    async def update(self, printer_id: str, configuration: PrinterConfiguration) -> PrinterSetupOutcome: ...

    async def remove(self, printer_id: str) -> None: ...

    async def reconnect(self, printer_id: str) -> PrinterSetupOutcome: ...
