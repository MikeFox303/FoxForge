# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from foxforge.application.fleet import FleetPrinterNotFoundError, FleetService
from foxforge.domain.printers import ConnectionState
from foxforge.testing import FakePrinterAdapter


def test_adapter_added_after_subscription_relays_connect_events(printer_identity) -> None:
    async def scenario() -> None:
        fleet = FleetService()
        events = fleet.events()
        adapter = FakePrinterAdapter(printer_identity)
        try:
            await fleet.add_adapter(adapter)
            assert fleet.printer_ids == (printer_identity.printer_id,)

            await fleet.connect(printer_identity.printer_id)
            assert fleet.snapshot(printer_identity.printer_id).connection == ConnectionState.CONNECTED

            event = await asyncio.wait_for(anext(events), timeout=0.5)
            assert event.printer_id == printer_identity.printer_id
        finally:
            await events.aclose()  # type: ignore[attr-defined]
            await fleet.aclose()

    asyncio.run(scenario())


def test_remove_adapter_disconnects_and_removes_printer(printer_identity) -> None:
    async def scenario() -> None:
        adapter = FakePrinterAdapter(printer_identity)
        fleet = FleetService([adapter])
        await fleet.connect(printer_identity.printer_id)

        await fleet.remove_adapter(printer_identity.printer_id)

        assert fleet.printer_ids == ()
        assert adapter.snapshot().connection == ConnectionState.DISCONNECTED
        with pytest.raises(FleetPrinterNotFoundError):
            fleet.snapshot(printer_identity.printer_id)
        await fleet.aclose()

    asyncio.run(scenario())


def test_dynamic_fleet_keeps_deterministic_identity_order(printer_identity) -> None:
    async def scenario() -> None:
        fleet = FleetService()
        try:
            later = replace(printer_identity, printer_id="z-printer", display_name="Z")
            earlier = replace(printer_identity, printer_id="a-printer", display_name="A")
            await fleet.add_adapter(FakePrinterAdapter(later))
            await fleet.add_adapter(FakePrinterAdapter(earlier))
            assert fleet.printer_ids == ("a-printer", "z-printer")
            assert [identity.printer_id for identity in fleet.identities()] == ["a-printer", "z-printer"]
        finally:
            await fleet.aclose()

    asyncio.run(scenario())
