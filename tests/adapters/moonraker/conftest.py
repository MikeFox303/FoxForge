# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from foxforge.adapters.moonraker import (
    MoonrakerNativeDispatchResult,
    MoonrakerNativePrintRequest,
    MoonrakerNativeState,
    MoonrakerTransportError,
)
from foxforge.domain.printers import PrinterIdentity, utc_now
from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat


class FakeMoonrakerTransport:
    def __init__(self, state: MoonrakerNativeState) -> None:
        self._state = state
        self._events: asyncio.Queue[MoonrakerNativeState | None] = asyncio.Queue()
        self.connect_count = 0
        self.disconnect_count = 0
        self.submit_count = 0
        self.submitted: list[MoonrakerNativePrintRequest] = []
        self.next_submit_error: MoonrakerTransportError | None = None

    async def connect(self) -> None:
        self.connect_count += 1
        self._state = replace(self._state, connected=True, klippy_state="ready", observed_at=utc_now())

    async def disconnect(self) -> None:
        self.disconnect_count += 1
        self._state = replace(self._state, connected=False, observed_at=utc_now())

    def snapshot(self) -> MoonrakerNativeState:
        return self._state

    async def events(self) -> AsyncIterator[MoonrakerNativeState]:
        while True:
            item = await self._events.get()
            if item is None:
                return
            self._state = item
            yield item

    async def submit_print(self, request: MoonrakerNativePrintRequest) -> MoonrakerNativeDispatchResult:
        self.submit_count += 1
        self.submitted.append(request)
        if self.next_submit_error is not None:
            error = self.next_submit_error
            self.next_submit_error = None
            raise error
        return MoonrakerNativeDispatchResult(accepted_at=utc_now(), vendor_job_id=request.filename)

    async def push(self, state: MoonrakerNativeState) -> None:
        await self._events.put(state)


@pytest.fixture
def moonraker_identity() -> PrinterIdentity:
    return PrinterIdentity(
        printer_id="moonraker-1",
        display_name="Ender 3 V3 KE",
        vendor="creality",
        model="Ender-3 V3 KE",
        serial_number=None,
        adapter_kind="moonraker",
    )


@pytest.fixture
def moonraker_idle_state() -> MoonrakerNativeState:
    return MoonrakerNativeState(
        connected=False,
        klippy_state="ready",
        klippy_message=None,
        print_state="standby",
        filename=None,
        progress=None,
        print_duration_seconds=None,
        print_message=None,
        observed_at=utc_now(),
    )


@pytest.fixture
def fake_moonraker_transport(moonraker_idle_state) -> FakeMoonrakerTransport:
    return FakeMoonrakerTransport(moonraker_idle_state)


@pytest.fixture
def moonraker_gcode(tmp_path: Path) -> LocalPrintArtifact:
    payload = b"; FoxForge test G-code\nG28\nG1 X10 Y10\n"
    path = tmp_path / "job.gcode"
    path.write_bytes(payload)
    return LocalPrintArtifact(
        artifact_id="gcode-1",
        path=path.resolve(),
        filename=path.name,
        format=PrintArtifactFormat.GCODE,
        size_bytes=len(payload),
        sha256=sha256(payload).hexdigest(),
    )
