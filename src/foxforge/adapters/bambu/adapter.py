# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import replace
from typing import TypeVar, cast
from uuid import uuid4

from foxforge.domain.printers import (
    ConnectionState,
    PrinterEvent,
    PrinterEventKind,
    PrinterIdentity,
    PrinterSnapshot,
    utc_now,
)
from foxforge.domain.printers.capabilities import MaterialSystemCapability, PrintExecutionCapability

from .mapping import map_bambu_material_system, map_bambu_state
from .material_system import BambuMaterialSystemCapability
from .native import BambuNativeState
from .print_execution import BambuPrintExecutionCapability, normalize_bambu_transport_error
from .transport import BambuTransport, BambuTransportError

C = TypeVar("C")


class _BambuEventSubscription(AsyncIterator[PrinterEvent]):
    def __init__(self, adapter: BambuAdapter) -> None:
        self._adapter = adapter
        self._queue: asyncio.Queue[PrinterEvent] = asyncio.Queue()
        self._closed = False
        adapter._subscribers.add(self._queue)

    def __aiter__(self) -> _BambuEventSubscription:
        return self

    async def __anext__(self) -> PrinterEvent:
        if self._closed:
            raise StopAsyncIteration
        return await self._queue.get()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._adapter._subscribers.discard(self._queue)


class BambuAdapter:
    """FoxForge anti-corruption adapter around an injected Bambu transport."""

    def __init__(self, identity: PrinterIdentity, transport: BambuTransport) -> None:
        if identity.adapter_kind != "bambu":
            raise ValueError("BambuAdapter requires identity.adapter_kind == 'bambu'")
        self._identity = identity
        self._transport = transport
        self._native = transport.snapshot()
        self._snapshot = map_bambu_state(identity.printer_id, self._native)
        self._subscribers: set[asyncio.Queue[PrinterEvent]] = set()
        self._connection_epoch = uuid4()
        self._sequence = 0
        self._pump_task: asyncio.Task[None] | None = None
        self._material = BambuMaterialSystemCapability(identity.printer_id, self.native_snapshot)
        self._printing = BambuPrintExecutionCapability(
            transport,
            self.snapshot,
            self.native_snapshot,
        )
        self._capabilities: dict[type[object], object] = {
            cast(type[object], MaterialSystemCapability): self._material,
            cast(type[object], PrintExecutionCapability): self._printing,
        }

    @property
    def identity(self) -> PrinterIdentity:
        return self._identity

    async def connect(self) -> None:
        if self._snapshot.connection in {ConnectionState.CONNECTED, ConnectionState.DEGRADED}:
            return
        try:
            await self._transport.connect()
            native = self._transport.snapshot()
        except BambuTransportError as error:
            raise normalize_bambu_transport_error(error) from error
        self._begin_epoch()
        self._apply_native(native, reconcile=True, begin_epoch_on_reconnect=False)
        if self._pump_task is None or self._pump_task.done():
            self._pump_task = asyncio.create_task(self._pump_events())

    async def disconnect(self) -> None:
        if self._snapshot.connection == ConnectionState.DISCONNECTED and self._pump_task is None:
            return
        task = self._pump_task
        self._pump_task = None
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        try:
            await self._transport.disconnect()
        except BambuTransportError as error:
            raise normalize_bambu_transport_error(error) from error
        native = replace(self._native, connected=False, observed_at=utc_now())
        self._apply_native(native, begin_epoch_on_reconnect=False)

    def snapshot(self) -> PrinterSnapshot:
        return self._snapshot

    def native_snapshot(self) -> BambuNativeState:
        return self._native

    def capability(self, capability_type: type[C]) -> C | None:
        value = self._capabilities.get(cast(type[object], capability_type))
        return cast(C | None, value)

    def events(self) -> AsyncIterator[PrinterEvent]:
        return _BambuEventSubscription(self)

    async def _pump_events(self) -> None:
        try:
            async for native in self._transport.events():
                self._apply_native(native)
        except asyncio.CancelledError:
            raise
        except BambuTransportError as error:
            degraded = replace(self._native, connected=False, observed_at=utc_now())
            self._apply_native(degraded, begin_epoch_on_reconnect=False)
            self._emit(PrinterEventKind.SNAPSHOT_RECONCILED, normalize_bambu_transport_error(error))

    def _apply_native(
        self,
        native: BambuNativeState,
        *,
        reconcile: bool = False,
        begin_epoch_on_reconnect: bool = True,
    ) -> None:
        previous_native = self._native
        previous = self._snapshot
        current = map_bambu_state(self._identity.printer_id, native)

        if (
            begin_epoch_on_reconnect
            and previous.connection == ConnectionState.DISCONNECTED
            and current.connection == ConnectionState.CONNECTED
        ):
            self._begin_epoch()

        self._native = native
        self._snapshot = current

        if previous.connection != current.connection:
            self._emit(PrinterEventKind.CONNECTION_CHANGED, current)
        if previous.operational_state != current.operational_state:
            self._emit(PrinterEventKind.PRINTER_STATE_CHANGED, current)

        previous_job_state = previous.active_job.state if previous.active_job else None
        current_job_state = current.active_job.state if current.active_job else None
        if previous_job_state != current_job_state:
            self._emit(PrinterEventKind.JOB_STATE_CHANGED, current.active_job)

        previous_progress = previous.active_job.progress if previous.active_job else None
        current_progress = current.active_job.progress if current.active_job else None
        if previous_progress != current_progress:
            self._emit(PrinterEventKind.JOB_PROGRESS_CHANGED, current.active_job)

        previous_material = map_bambu_material_system(self._identity.printer_id, previous_native)
        current_material = map_bambu_material_system(self._identity.printer_id, native)
        if previous_material.units != current_material.units or previous_material.stale != current_material.stale:
            self._emit(PrinterEventKind.MATERIAL_SYSTEM_CHANGED, current_material)

        if reconcile:
            self._emit(PrinterEventKind.SNAPSHOT_RECONCILED, current)

    def _begin_epoch(self) -> None:
        self._connection_epoch = uuid4()
        self._sequence = 0

    def _emit(self, kind: PrinterEventKind, payload: object) -> PrinterEvent:
        self._sequence += 1
        now = utc_now()
        event = PrinterEvent(
            event_id=uuid4(),
            printer_id=self._identity.printer_id,
            connection_epoch=self._connection_epoch,
            sequence=self._sequence,
            observed_at=self._native.observed_at,
            emitted_at=now,
            kind=kind,
            payload=payload,
        )
        for queue in tuple(self._subscribers):
            queue.put_nowait(event)
        return event
