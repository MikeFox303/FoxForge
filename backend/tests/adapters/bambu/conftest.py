# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from foxforge.adapters.bambu import (
    BambuMaterialUnitKind,
    BambuNativeDispatchResult,
    BambuNativeMaterialUnit,
    BambuNativePrintRequest,
    BambuNativeState,
    BambuNativeTray,
    BambuTransportError,
)
from foxforge.domain.printers import PrinterIdentity, utc_now
from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat


class FakeBambuTransport:
    def __init__(self, state: BambuNativeState) -> None:
        self._state = state
        self._events: asyncio.Queue[BambuNativeState | None] = asyncio.Queue()
        self.connect_count = 0
        self.disconnect_count = 0
        self.submit_count = 0
        self.submitted: list[BambuNativePrintRequest] = []
        self.next_submit_error: BambuTransportError | None = None

    async def connect(self) -> None:
        self.connect_count += 1
        self._state = _with_connection(self._state, True)

    async def disconnect(self) -> None:
        self.disconnect_count += 1
        self._state = _with_connection(self._state, False)

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
        self.submit_count += 1
        self.submitted.append(request)
        if self.next_submit_error is not None:
            error = self.next_submit_error
            self.next_submit_error = None
            raise error
        return BambuNativeDispatchResult(accepted_at=utc_now(), vendor_job_id=f"bambu-job-{self.submit_count}")

    async def push(self, state: BambuNativeState) -> None:
        await self._events.put(state)


@pytest.fixture
def bambu_identity() -> PrinterIdentity:
    return PrinterIdentity(
        printer_id="bambu-1",
        display_name="X2D",
        vendor="bambu_lab",
        model="X2D",
        serial_number="N6TEST",
        adapter_kind="bambu",
    )


@pytest.fixture
def bambu_idle_state() -> BambuNativeState:
    return BambuNativeState(
        connected=False,
        gcode_state="IDLE",
        current_print=None,
        vendor_job_id=None,
        progress_percent=None,
        remaining_minutes=None,
        layer_num=None,
        total_layers=None,
        faults=(),
        material_units=(
            BambuNativeMaterialUnit(
                ams_id=0,
                kind=BambuMaterialUnitKind.AMS_2_PRO,
                label="AMS 2 Pro A",
                trays=(
                    BambuNativeTray(
                        ams_id=0,
                        tray_id=0,
                        material_type="PETG",
                        vendor_name="SUNLU",
                        product_name="PETG",
                        color_rgba="ff6600ff",
                        tag_uid="tag-001",
                        remaining_percent=80,
                        exists=True,
                        active=False,
                    ),
                    BambuNativeTray(
                        ams_id=0,
                        tray_id=1,
                        material_type="PLA",
                        vendor_name="Bambu Lab",
                        product_name="Support for PLA/PETG",
                        color_rgba="FFFFFFFF",
                        tag_uid="tag-002",
                        remaining_percent=55,
                        exists=True,
                        active=False,
                    ),
                ),
            ),
        ),
        observed_at=utc_now(),
    )


@pytest.fixture
def fake_bambu_transport(bambu_idle_state) -> FakeBambuTransport:
    return FakeBambuTransport(bambu_idle_state)


@pytest.fixture
def bambu_3mf(tmp_path: Path) -> LocalPrintArtifact:
    return make_3mf(tmp_path / "job.3mf")


def make_3mf(path: Path) -> LocalPrintArtifact:
    payload = b"PK\x03\x04foxforge-test-3mf"
    path.write_bytes(payload)
    return LocalPrintArtifact(
        artifact_id="3mf-1",
        path=path.resolve(),
        filename=path.name,
        format=PrintArtifactFormat.THREE_MF,
        size_bytes=len(payload),
        sha256=sha256(payload).hexdigest(),
    )


def _with_connection(state: BambuNativeState, connected: bool) -> BambuNativeState:
    return replace(state, connected=connected, observed_at=utc_now())
