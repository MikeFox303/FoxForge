# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace

import pytest

from foxforge.adapters.bambu import (
    BambuAdapter,
    BambuNativeDispatchResult,
    BambuNativePrintRequest,
    BambuNativeState,
)
from foxforge.application.fleet import DuplicatePrinterIdError, FleetPrinterNotFoundError, FleetService
from foxforge.domain.printers import ConnectionState, OperationalState, PrinterIdentity, utc_now
from foxforge.domain.printers.capabilities import PrintExecutionCapability
from foxforge.testing import FakePrinterAdapter


class _FleetBambuTransport:
    def __init__(self) -> None:
        self._state = BambuNativeState(
            connected=False,
            gcode_state="IDLE",
            current_print=None,
            vendor_job_id=None,
            progress_percent=None,
            remaining_minutes=None,
            layer_num=None,
            total_layers=None,
            faults=(),
            material_units=(),
            observed_at=utc_now(),
        )
        self._events: asyncio.Queue[BambuNativeState | None] = asyncio.Queue()

    async def connect(self) -> None:
        self._state = replace(self._state, connected=True, observed_at=utc_now())

    async def disconnect(self) -> None:
        self._state = replace(self._state, connected=False, observed_at=utc_now())

    def snapshot(self) -> BambuNativeState:
        return self._state

    async def events(self) -> AsyncIterator[BambuNativeState]:
        while True:
            item = await self._events.get()
            if item is None:
                return
            self._state = item
            yield item

    async def submit_print(self, request: BambuNativePrintRequest) -> BambuNativeDispatchResult:
        return BambuNativeDispatchResult(accepted_at=utc_now(), vendor_job_id="fleet-bambu-job")


def _make_bambu_adapter() -> BambuAdapter:
    identity = PrinterIdentity(
        printer_id="bambu-1",
        display_name="Bambu X2D",
        vendor="bambu_lab",
        model="X2D",
        serial_number="N6FLEET",
        adapter_kind="bambu",
    )
    return BambuAdapter(identity, _FleetBambuTransport())


def test_fake_and_bambu_can_coexist_in_one_fleet(printer_identity) -> None:
    async def scenario() -> None:
        fake = FakePrinterAdapter(printer_identity)
        bambu = _make_bambu_adapter()
        fleet = FleetService([fake, bambu])
        try:
            assert fleet.printer_ids == ("bambu-1", "printer-1")
            assert [identity.adapter_kind for identity in fleet.identities()] == ["bambu", "fake"]

            await fleet.connect_all()

            snapshots = fleet.snapshots()
            assert {snapshot.printer_id for snapshot in snapshots} == {"bambu-1", "printer-1"}
            assert all(snapshot.connection == ConnectionState.CONNECTED for snapshot in snapshots)
            assert all(snapshot.operational_state == OperationalState.IDLE for snapshot in snapshots)
            assert fleet.capability("bambu-1", PrintExecutionCapability) is not None
            assert fleet.capability("printer-1", PrintExecutionCapability) is None

            await fleet.disconnect_all()
            assert all(snapshot.connection == ConnectionState.DISCONNECTED for snapshot in fleet.snapshots())
        finally:
            await fleet.aclose()

    asyncio.run(scenario())


def test_fleet_merges_normalized_events_from_multiple_adapters(printer_identity) -> None:
    async def scenario() -> None:
        fleet = FleetService([FakePrinterAdapter(printer_identity), _make_bambu_adapter()])
        events = fleet.events()
        try:
            await fleet.connect_all()
            seen_printers: set[str] = set()
            for _ in range(12):
                event = await asyncio.wait_for(anext(events), timeout=0.5)
                seen_printers.add(event.printer_id)
                if seen_printers == {"bambu-1", "printer-1"}:
                    break

            assert seen_printers == {"bambu-1", "printer-1"}
        finally:
            await events.aclose()  # type: ignore[attr-defined]
            await fleet.aclose()

    asyncio.run(scenario())


def test_fleet_rejects_duplicate_printer_ids(printer_identity) -> None:
    with pytest.raises(DuplicatePrinterIdError):
        FleetService([FakePrinterAdapter(printer_identity), FakePrinterAdapter(printer_identity)])


def test_fleet_unknown_printer_is_explicit(printer_identity) -> None:
    fleet = FleetService([FakePrinterAdapter(printer_identity)])

    with pytest.raises(FleetPrinterNotFoundError) as caught:
        fleet.snapshot("missing")

    assert caught.value.printer_id == "missing"
