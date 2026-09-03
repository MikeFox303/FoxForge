# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from typing import TypeVar

from foxforge.domain.printers import PrinterAdapter, PrinterEvent, PrinterIdentity, PrinterSnapshot

C = TypeVar("C")


class FleetPrinterNotFoundError(KeyError):
    def __init__(self, printer_id: str) -> None:
        self.printer_id = printer_id
        super().__init__(printer_id)


class DuplicatePrinterIdError(ValueError):
    def __init__(self, printer_id: str) -> None:
        self.printer_id = printer_id
        super().__init__(f"duplicate printer id in fleet: {printer_id}")


class _FleetEventSubscription(AsyncIterator[PrinterEvent]):
    def __init__(self, fleet: FleetService) -> None:
        self._fleet = fleet
        self._queue: asyncio.Queue[PrinterEvent] = asyncio.Queue()
        self._closed = False
        fleet._subscribers.add(self._queue)

    def __aiter__(self) -> _FleetEventSubscription:
        return self

    async def __anext__(self) -> PrinterEvent:
        if self._closed:
            raise StopAsyncIteration
        return await self._queue.get()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._fleet._subscribers.discard(self._queue)


class FleetService:
    """Application-level view of a fixed set of printer adapters.

    FleetService depends only on the common PrinterAdapter contract. Vendor
    selection belongs in the composition root/AdapterRegistry, not here.
    """

    def __init__(self, adapters: Iterable[PrinterAdapter] = ()) -> None:
        self._adapters: dict[str, PrinterAdapter] = {}
        self._subscribers: set[asyncio.Queue[PrinterEvent]] = set()
        self._relay_tasks: dict[str, asyncio.Task[None]] = {}
        self._closed = False

        for adapter in adapters:
            printer_id = adapter.identity.printer_id
            if printer_id in self._adapters:
                raise DuplicatePrinterIdError(printer_id)
            self._adapters[printer_id] = adapter

    @property
    def printer_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def identities(self) -> tuple[PrinterIdentity, ...]:
        return tuple(self._adapters[printer_id].identity for printer_id in self.printer_ids)

    def snapshots(self) -> tuple[PrinterSnapshot, ...]:
        return tuple(self._adapters[printer_id].snapshot() for printer_id in self.printer_ids)

    def snapshot(self, printer_id: str) -> PrinterSnapshot:
        return self._require_adapter(printer_id).snapshot()

    def capability(self, printer_id: str, capability_type: type[C]) -> C | None:
        return self._require_adapter(printer_id).capability(capability_type)

    async def connect(self, printer_id: str) -> None:
        self._ensure_open()
        await self._require_adapter(printer_id).connect()

    async def disconnect(self, printer_id: str) -> None:
        self._ensure_open()
        await self._require_adapter(printer_id).disconnect()

    async def connect_all(self) -> None:
        self._ensure_open()
        for printer_id in self.printer_ids:
            await self._adapters[printer_id].connect()

    async def disconnect_all(self) -> None:
        self._ensure_open()
        for printer_id in reversed(self.printer_ids):
            await self._adapters[printer_id].disconnect()

    def events(self) -> AsyncIterator[PrinterEvent]:
        self._ensure_open()
        # Relays require an active asyncio loop, which is also the only context
        # in which consuming an AsyncIterator is meaningful.
        asyncio.get_running_loop()
        subscription = _FleetEventSubscription(self)
        self._ensure_relays()
        return subscription

    async def aclose(self) -> None:
        if self._closed:
            return

        await self.disconnect_all()
        self._closed = True

        tasks = tuple(self._relay_tasks.values())
        self._relay_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._subscribers.clear()

    def _require_adapter(self, printer_id: str) -> PrinterAdapter:
        adapter = self._adapters.get(printer_id)
        if adapter is None:
            raise FleetPrinterNotFoundError(printer_id)
        return adapter

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("fleet service is closed")

    def _ensure_relays(self) -> None:
        for printer_id, adapter in self._adapters.items():
            task = self._relay_tasks.get(printer_id)
            if task is None or task.done():
                self._relay_tasks[printer_id] = asyncio.create_task(self._relay_events(adapter))

    async def _relay_events(self, adapter: PrinterAdapter) -> None:
        stream = adapter.events()
        try:
            async for event in stream:
                self._emit(event)
        except asyncio.CancelledError:
            raise
        finally:
            close = getattr(stream, "aclose", None)
            if close is not None:
                await close()

    def _emit(self, event: PrinterEvent) -> None:
        for queue in tuple(self._subscribers):
            queue.put_nowait(event)
