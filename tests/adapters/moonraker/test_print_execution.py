# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from foxforge.adapters.moonraker import (
    MOONRAKER_EXTERNAL_SLOT_ID,
    MoonrakerAdapter,
    MoonrakerTransportError,
    MoonrakerTransportErrorKind,
)
from foxforge.domain.printers import PrinterAdapterError, PrinterErrorCode
from foxforge.domain.printers.capabilities import (
    MaterialBinding,
    PrintArtifactSelection,
    PrintExecutionCapability,
    PrintExecutionRequest,
)


def test_valid_gcode_assessment_and_submit_are_idempotent(
    moonraker_identity,
    fake_moonraker_transport,
    moonraker_gcode,
) -> None:
    async def scenario() -> None:
        adapter = MoonrakerAdapter(moonraker_identity, fake_moonraker_transport)
        await adapter.connect()
        capability = adapter.capability(PrintExecutionCapability)
        assert capability is not None
        request = PrintExecutionRequest(
            dispatch_id=uuid4(),
            artifact=moonraker_gcode,
            material_bindings=(MaterialBinding(material_index=0, slot_id=MOONRAKER_EXTERNAL_SLOT_ID),),
        )

        assessment = await capability.assess(request)
        assert assessment.eligible is True
        first = await capability.submit(request)
        second = await capability.submit(request)

        assert first == second
        assert fake_moonraker_transport.submit_count == 1
        assert fake_moonraker_transport.submitted[0].filename == moonraker_gcode.filename
        assert fake_moonraker_transport.submitted[0].sha256 == moonraker_gcode.sha256
        await adapter.disconnect()

    asyncio.run(scenario())


def test_plate_selection_is_rejected(moonraker_identity, fake_moonraker_transport, moonraker_gcode) -> None:
    async def scenario() -> None:
        adapter = MoonrakerAdapter(moonraker_identity, fake_moonraker_transport)
        await adapter.connect()
        capability = adapter.capability(PrintExecutionCapability)
        assert capability is not None
        request = PrintExecutionRequest(
            dispatch_id=uuid4(),
            artifact=moonraker_gcode,
            selection=PrintArtifactSelection(plate_index=0),
        )

        assessment = await capability.assess(request)
        assert assessment.eligible is False
        assert any(blocker.code.value == "unsupported_selection" for blocker in assessment.blockers)
        await adapter.disconnect()

    asyncio.run(scenario())


def test_indeterminate_transport_error_is_normalized(
    moonraker_identity,
    fake_moonraker_transport,
    moonraker_gcode,
) -> None:
    async def scenario() -> None:
        adapter = MoonrakerAdapter(moonraker_identity, fake_moonraker_transport)
        await adapter.connect()
        capability = adapter.capability(PrintExecutionCapability)
        assert capability is not None
        fake_moonraker_transport.next_submit_error = MoonrakerTransportError(
            MoonrakerTransportErrorKind.INDETERMINATE,
            "connection dropped after start",
            vendor_code="ws_closed",
        )
        request = PrintExecutionRequest(dispatch_id=uuid4(), artifact=moonraker_gcode)

        with pytest.raises(PrinterAdapterError) as caught:
            await capability.submit(request)
        assert caught.value.code == PrinterErrorCode.INDETERMINATE
        assert caught.value.retryable is False
        assert caught.value.vendor_code == "ws_closed"
        await adapter.disconnect()

    asyncio.run(scenario())
