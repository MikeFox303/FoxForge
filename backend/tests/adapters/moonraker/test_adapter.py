# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace

from foxforge.adapters.moonraker import MoonrakerAdapter, MoonrakerNativeThermalZone
from foxforge.domain.printers import ConnectionState, OperationalState, PrinterEventKind, utc_now
from foxforge.domain.printers.capabilities import (
    MaterialSystemCapability,
    MaterialTopologyCapability,
    PrintExecutionCapability,
    ThermalTelemetryCapability,
)


def test_moonraker_adapter_lifecycle_is_idempotent(moonraker_identity, fake_moonraker_transport) -> None:
    async def scenario() -> None:
        adapter = MoonrakerAdapter(moonraker_identity, fake_moonraker_transport)

        assert adapter.snapshot().connection == ConnectionState.DISCONNECTED
        await adapter.connect()
        await adapter.connect()
        assert fake_moonraker_transport.connect_count == 1
        assert adapter.snapshot().connection == ConnectionState.CONNECTED
        assert adapter.snapshot().operational_state == OperationalState.IDLE

        await adapter.disconnect()
        await adapter.disconnect()
        assert fake_moonraker_transport.disconnect_count == 1
        assert adapter.snapshot().connection == ConnectionState.DISCONNECTED

    asyncio.run(scenario())


def test_moonraker_adapter_resolves_common_capabilities(moonraker_identity, fake_moonraker_transport) -> None:
    adapter = MoonrakerAdapter(moonraker_identity, fake_moonraker_transport)

    assert adapter.capability(PrintExecutionCapability) is not None
    assert adapter.capability(MaterialSystemCapability) is not None
    assert adapter.capability(ThermalTelemetryCapability) is not None
    assert adapter.capability(MaterialTopologyCapability) is None
    assert adapter.capability(dict) is None


def test_moonraker_native_updates_emit_normalized_events(
    moonraker_identity,
    fake_moonraker_transport,
    moonraker_idle_state,
) -> None:
    async def scenario() -> None:
        adapter = MoonrakerAdapter(moonraker_identity, fake_moonraker_transport)
        await adapter.connect()
        events = adapter.events()
        try:
            running = replace(
                moonraker_idle_state,
                connected=True,
                print_state="printing",
                filename="part.gcode",
                progress=0.1,
                print_duration_seconds=5.0,
                observed_at=utc_now(),
            )
            await fake_moonraker_transport.push(running)

            observed = [await asyncio.wait_for(anext(events), timeout=0.2) for _ in range(3)]
            assert [event.kind for event in observed] == [
                PrinterEventKind.PRINTER_STATE_CHANGED,
                PrinterEventKind.JOB_STATE_CHANGED,
                PrinterEventKind.JOB_PROGRESS_CHANGED,
            ]
            assert adapter.snapshot().operational_state == OperationalState.PRINTING
            assert len({event.connection_epoch for event in observed}) == 1
        finally:
            await events.aclose()  # type: ignore[attr-defined]
            await adapter.disconnect()

    asyncio.run(scenario())


def test_moonraker_thermal_update_emits_common_event(
    moonraker_identity,
    fake_moonraker_transport,
    moonraker_idle_state,
) -> None:
    async def scenario() -> None:
        adapter = MoonrakerAdapter(moonraker_identity, fake_moonraker_transport)
        await adapter.connect()
        events = adapter.events()
        try:
            thermal = replace(
                moonraker_idle_state,
                connected=True,
                thermal_zones=(
                    MoonrakerNativeThermalZone("extruder", 0, 205.0, 210.0),
                    MoonrakerNativeThermalZone("heater_bed", 0, 59.0, 60.0),
                ),
                observed_at=utc_now(),
            )
            await fake_moonraker_transport.push(thermal)
            event = await asyncio.wait_for(anext(events), timeout=0.2)
            assert event.kind == PrinterEventKind.THERMAL_TELEMETRY_CHANGED
            snapshot = event.payload
            assert snapshot.stale is False
            assert [(zone.zone_id, zone.label) for zone in snapshot.zones] == [
                ("hotend:0", "Hotend"),
                ("bed:0", "Bed"),
            ]
        finally:
            await events.aclose()  # type: ignore[attr-defined]
            await adapter.disconnect()

    asyncio.run(scenario())


def test_moonraker_reconnect_starts_new_event_epoch(
    moonraker_identity,
    fake_moonraker_transport,
    moonraker_idle_state,
) -> None:
    async def scenario() -> None:
        adapter = MoonrakerAdapter(moonraker_identity, fake_moonraker_transport)
        await adapter.connect()
        events = adapter.events()
        try:
            offline = replace(moonraker_idle_state, connected=False, observed_at=utc_now())
            online = replace(moonraker_idle_state, connected=True, observed_at=utc_now())

            await fake_moonraker_transport.push(offline)
            offline_events = [await asyncio.wait_for(anext(events), timeout=0.2) for _ in range(3)]
            assert [event.kind for event in offline_events] == [
                PrinterEventKind.CONNECTION_CHANGED,
                PrinterEventKind.PRINTER_STATE_CHANGED,
                PrinterEventKind.MATERIAL_SYSTEM_CHANGED,
            ]
            offline_epoch = offline_events[0].connection_epoch

            await fake_moonraker_transport.push(online)
            online_events = [await asyncio.wait_for(anext(events), timeout=0.2) for _ in range(3)]
            assert [event.kind for event in online_events] == [
                PrinterEventKind.CONNECTION_CHANGED,
                PrinterEventKind.PRINTER_STATE_CHANGED,
                PrinterEventKind.MATERIAL_SYSTEM_CHANGED,
            ]
            online_epoch = online_events[0].connection_epoch
            assert online_epoch != offline_epoch
            assert [event.sequence for event in online_events] == [1, 2, 3]
        finally:
            await events.aclose()  # type: ignore[attr-defined]
            await adapter.disconnect()

    asyncio.run(scenario())
