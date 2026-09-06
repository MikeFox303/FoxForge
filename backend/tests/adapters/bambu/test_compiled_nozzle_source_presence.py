# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest

from foxforge.adapters.bambu.mapping import map_bambu_state
from foxforge.adapters.bambu.print_execution import BambuPrintExecutionCapability
from foxforge.domain.printers import PrinterAdapterError, PrinterErrorCode, utc_now
from foxforge.domain.printers.capabilities import (
    MaterialBinding,
    PrintAssessmentBlockerCode,
    PrintExecutionRequest,
)


def test_compiled_bambu_route_blocks_when_source_is_no_longer_confirmed_loaded(
    bambu_identity,
    fake_bambu_transport,
    bambu_3mf,
) -> None:
    async def scenario() -> None:
        base = replace(fake_bambu_transport.snapshot(), connected=True, observed_at=utc_now())
        unit = base.material_units[0]
        absent_tray = replace(unit.trays[0], exists=False)
        native = replace(
            base,
            material_units=(replace(unit, trays=(absent_tray, *unit.trays[1:])),),
            observed_at=utc_now(),
        )
        printing = BambuPrintExecutionCapability(
            fake_bambu_transport,
            lambda: map_bambu_state(bambu_identity.printer_id, native),
            lambda: native,
        )
        request = PrintExecutionRequest(
            uuid4(),
            bambu_3mf,
            material_bindings=(
                MaterialBinding(0, "bambu:unit:0:tray:0", "bambu:toolhead:0"),
            ),
        )

        assessment = await printing.assess(request)

        assert not assessment.eligible
        assert assessment.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE
        with pytest.raises(PrinterAdapterError) as caught:
            await printing.submit(request)
        assert caught.value.code == PrinterErrorCode.NOT_READY
        assert fake_bambu_transport.submit_count == 0

    asyncio.run(scenario())


def test_compiled_bambu_route_blocks_stale_native_topology(
    bambu_identity,
    fake_bambu_transport,
    bambu_3mf,
) -> None:
    async def scenario() -> None:
        connected = replace(fake_bambu_transport.snapshot(), connected=True, observed_at=utc_now())
        stale_native = replace(connected, connected=False, observed_at=utc_now())
        printing = BambuPrintExecutionCapability(
            fake_bambu_transport,
            lambda: map_bambu_state(bambu_identity.printer_id, connected),
            lambda: stale_native,
        )
        request = PrintExecutionRequest(
            uuid4(),
            bambu_3mf,
            material_bindings=(
                MaterialBinding(0, "bambu:unit:0:tray:0", "bambu:toolhead:0"),
            ),
        )

        assessment = await printing.assess(request)

        assert not assessment.eligible
        assert assessment.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE
        assert fake_bambu_transport.submit_count == 0

    asyncio.run(scenario())
