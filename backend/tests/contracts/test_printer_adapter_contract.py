# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

from foxforge.domain.printers import ConnectionState, OperationalState, PrinterEventKind
from foxforge.domain.printers.capabilities import PrintExecutionCapability
from foxforge.testing import FakePrinterAdapter, FakePrintExecutionCapability


def test_identity_and_snapshot_are_available_before_connection(printer_identity) -> None:
    adapter = FakePrinterAdapter(printer_identity)

    assert adapter.identity is printer_identity
    snapshot = adapter.snapshot()
    assert snapshot.printer_id == printer_identity.printer_id
    assert snapshot.connection == ConnectionState.DISCONNECTED
    assert snapshot.operational_state == OperationalState.OFFLINE


def test_connect_and_disconnect_are_idempotent(printer_identity) -> None:
    async def scenario() -> None:
        adapter = FakePrinterAdapter(printer_identity)

        await adapter.connect()
        first_epoch_count = adapter.transport_connect_count
        await adapter.connect()
        assert adapter.transport_connect_count == first_epoch_count == 1
        assert adapter.snapshot().connection == ConnectionState.CONNECTED

        await adapter.disconnect()
        first_disconnect_count = adapter.transport_disconnect_count
        await adapter.disconnect()
        assert adapter.transport_disconnect_count == first_disconnect_count == 1
        assert adapter.snapshot().connection == ConnectionState.DISCONNECTED

    asyncio.run(scenario())


def test_capability_resolution_returns_stable_object(printer_identity) -> None:
    adapter = FakePrinterAdapter(printer_identity)
    capability = FakePrintExecutionCapability(adapter)
    adapter.register_capability(PrintExecutionCapability, capability)

    assert adapter.capability(PrintExecutionCapability) is capability
    assert adapter.capability(PrintExecutionCapability) is capability
    assert adapter.capability(dict) is None


def test_event_subscriptions_are_independent_and_ordered(printer_identity) -> None:
    async def scenario() -> None:
        adapter = FakePrinterAdapter(printer_identity)
        first = adapter.events()
        second = adapter.events()
        try:
            await adapter.connect()
            first_events = [await asyncio.wait_for(anext(first), timeout=0.1) for _ in range(2)]
            second_events = [await asyncio.wait_for(anext(second), timeout=0.1) for _ in range(2)]

            assert [event.kind for event in first_events] == [
                PrinterEventKind.CONNECTION_CHANGED,
                PrinterEventKind.SNAPSHOT_RECONCILED,
            ]
            assert [event.event_id for event in first_events] == [event.event_id for event in second_events]
            assert [event.sequence for event in first_events] == [1, 2]
            assert len({event.connection_epoch for event in first_events}) == 1
        finally:
            await first.aclose()  # type: ignore[attr-defined]
            await second.aclose()  # type: ignore[attr-defined]

    asyncio.run(scenario())


def test_reconnect_creates_new_connection_epoch(printer_identity) -> None:
    async def scenario() -> None:
        adapter = FakePrinterAdapter(printer_identity)
        events = adapter.events()
        try:
            await adapter.connect()
            first_connected = await anext(events)
            await anext(events)  # reconciliation event
            await adapter.disconnect()
            await anext(events)
            await adapter.connect()
            second_connected = await anext(events)

            assert first_connected.connection_epoch != second_connected.connection_epoch
            assert second_connected.sequence == 1
        finally:
            await events.aclose()  # type: ignore[attr-defined]

    asyncio.run(scenario())
