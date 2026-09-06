# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace

from foxforge.adapters.bambu import BambuAdapter
from foxforge.domain.printers import ConnectionState, OperationalState, PrinterEventKind, utc_now
from foxforge.domain.printers.capabilities import (
    MaterialSystemCapability,
    MaterialTopologyCapability,
    PrintExecutionCapability,
)


def test_bambu_adapter_lifecycle_is_idempotent(bambu_identity, fake_bambu_transport) -> None:
    async def scenario() -> None:
        adapter = BambuAdapter(bambu_identity, fake_bambu_transport)

        assert adapter.snapshot().connection == ConnectionState.DISCONNECTED
        await adapter.connect()
        await adapter.connect()
        assert fake_bambu_transport.connect_count == 1
        assert adapter.snapshot().connection == ConnectionState.CONNECTED
        assert adapter.snapshot().operational_state == OperationalState.IDLE

        await adapter.disconnect()
        await adapter.disconnect()
        assert fake_bambu_transport.disconnect_count == 1
        assert adapter.snapshot().connection == ConnectionState.DISCONNECTED

    asyncio.run(scenario())


def test_bambu_adapter_resolves_common_capabilities(bambu_identity, fake_bambu_transport) -> None:
    adapter = BambuAdapter(bambu_identity, fake_bambu_transport)

    assert adapter.capability(PrintExecutionCapability) is not None
    assert adapter.capability(MaterialSystemCapability) is not None
    assert adapter.capability(MaterialTopologyCapability) is not None
    assert adapter.capability(dict) is None


def test_bambu_native_updates_emit_normalized_events(bambu_identity, fake_bambu_transport, bambu_idle_state) -> None:
    async def scenario() -> None:
        adapter = BambuAdapter(bambu_identity, fake_bambu_transport)
        await adapter.connect()
        events = adapter.events()
        try:
            running = replace(
                bambu_idle_state,
                connected=True,
                gcode_state="RUNNING",
                current_print="part.3mf",
                vendor_job_id="job-1",
                progress_percent=10,
                remaining_minutes=5,
                layer_num=1,
                total_layers=10,
                observed_at=utc_now(),
            )
            await fake_bambu_transport.push(running)

            observed = [await asyncio.wait_for(anext(events), timeout=0.2) for _ in range(3)]
            assert [event.kind for event in observed] == [
                PrinterEventKind.PRINTER_STATE_CHANGED,
                PrinterEventKind.JOB_STATE_CHANGED,
                PrinterEventKind.JOB_PROGRESS_CHANGED,
            ]
            assert len({event.connection_epoch for event in observed}) == 1
            assert adapter.snapshot().operational_state == OperationalState.PRINTING
        finally:
            await events.aclose()  # type: ignore[attr-defined]
            await adapter.disconnect()

    asyncio.run(scenario())


def test_transport_reconnect_starts_new_event_epoch(bambu_identity, fake_bambu_transport, bambu_idle_state) -> None:
    async def scenario() -> None:
        adapter = BambuAdapter(bambu_identity, fake_bambu_transport)
        await adapter.connect()
        events = adapter.events()
        try:
            offline = replace(bambu_idle_state, connected=False, observed_at=utc_now())
            online = replace(bambu_idle_state, connected=True, observed_at=utc_now())

            await fake_bambu_transport.push(offline)
            offline_events = [await asyncio.wait_for(anext(events), timeout=0.2) for _ in range(4)]
            assert [event.kind for event in offline_events] == [
                PrinterEventKind.CONNECTION_CHANGED,
                PrinterEventKind.PRINTER_STATE_CHANGED,
                PrinterEventKind.MATERIAL_SYSTEM_CHANGED,
                PrinterEventKind.MATERIAL_TOPOLOGY_CHANGED,
            ]
            offline_epoch = offline_events[0].connection_epoch
            assert all(event.connection_epoch == offline_epoch for event in offline_events)

            await fake_bambu_transport.push(online)
            online_events = [await asyncio.wait_for(anext(events), timeout=0.2) for _ in range(4)]
            assert [event.kind for event in online_events] == [
                PrinterEventKind.CONNECTION_CHANGED,
                PrinterEventKind.PRINTER_STATE_CHANGED,
                PrinterEventKind.MATERIAL_SYSTEM_CHANGED,
                PrinterEventKind.MATERIAL_TOPOLOGY_CHANGED,
            ]
            online_epoch = online_events[0].connection_epoch
            assert online_epoch != offline_epoch
            assert [event.sequence for event in online_events] == [1, 2, 3, 4]
        finally:
            await events.aclose()  # type: ignore[attr-defined]
            await adapter.disconnect()

    asyncio.run(scenario())
