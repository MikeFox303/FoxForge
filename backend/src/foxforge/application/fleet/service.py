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
    """Application-level dynamic collection of printer adapters.

    FleetService depends only on the common PrinterAdapter contract. Vendor
    selection belongs in the composition root/AdapterRegistry, not here. New
    adapters may be added and removed at runtime so printer configuration can
    be managed through FoxForge without restarting the server.
    """

    def __init__(self, adapters: Iterable[PrinterAdapter] = ()) -> None:
        self._adapters: dict[str, PrinterAdapter] = {}
        self._subscribers: set[asyncio.Queue[PrinterEvent]] = set()
        self._relay_tasks: dict[str, asyncio.Task[None]] = {}
        self._relay_ready: dict[str, asyncio.Event] = {}
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

    async def add_adapter(self, adapter: PrinterAdapter) -> None:
        """Add one already-constructed adapter to the live fleet.

        If fleet event relays are already active, the new adapter is subscribed
        before this method returns so connect-time events cannot be lost.
        Connection remains an explicit separate operation.
        """

        self._ensure_open()
        printer_id = adapter.identity.printer_id
        if printer_id in self._adapters:
            raise DuplicatePrinterIdError(printer_id)
        self._adapters[printer_id] = adapter

        if self._subscribers or self._relay_tasks:
            self._ensure_relays()
            ready = self._relay_ready.get(printer_id)
            if ready is not None:
                await ready.wait()

    async def remove_adapter(self, printer_id: str) -> None:
        """Disconnect and remove one adapter from the live fleet.

        The adapter is removed even if disconnect reports a normalized transport
        error. This is important for deleting an unreachable configured printer;
        callers may still observe the disconnect error if they need diagnostics.
        """

        self._ensure_open()
        adapter = self._require_adapter(printer_id)
        await self._stop_relay(printer_id)
        disconnect_error: BaseException | None = None
        try:
            await adapter.disconnect()
        except BaseException as error:
            disconnect_error = error
        finally:
            self._adapters.pop(printer_id, None)

        if disconnect_error is not None:
            raise disconnect_error

    async def connect(self, printer_id: str) -> None:
        self._ensure_open()
        adapter = self._require_adapter(printer_id)
        await self._ensure_relays_ready()
        await adapter.connect()

    async def disconnect(self, printer_id: str) -> None:
        self._ensure_open()
        await self._require_adapter(printer_id).disconnect()

    async def connect_all(self) -> None:
        self._ensure_open()
        await self._ensure_relays_ready()
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
        self._relay_ready.clear()
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
                ready = asyncio.Event()
                self._relay_ready[printer_id] = ready
                self._relay_tasks[printer_id] = asyncio.create_task(self._relay_events(adapter, ready))

    async def _ensure_relays_ready(self) -> None:
        self._ensure_relays()
        if self._relay_ready:
            await asyncio.gather(*(ready.wait() for ready in self._relay_ready.values()))

    async def _stop_relay(self, printer_id: str) -> None:
        task = self._relay_tasks.pop(printer_id, None)
        self._relay_ready.pop(printer_id, None)
        if task is None:
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _relay_events(self, adapter: PrinterAdapter, ready: asyncio.Event) -> None:
        stream = adapter.events()
        ready.set()
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
