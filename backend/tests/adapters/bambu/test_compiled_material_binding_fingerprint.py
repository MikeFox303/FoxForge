# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest

from foxforge.adapters.bambu import BambuAdapter
from foxforge.domain.printers import PrinterAdapterError, PrinterErrorCode
from foxforge.domain.printers.capabilities import MaterialBinding, PrintExecutionCapability, PrintExecutionRequest


def test_bambu_dispatch_id_conflicts_when_compiled_toolhead_changes(
    bambu_identity,
    fake_bambu_transport,
    bambu_3mf,
) -> None:
    async def scenario() -> None:
        adapter = BambuAdapter(bambu_identity, fake_bambu_transport)
        await adapter.connect()
        printing = adapter.capability(PrintExecutionCapability)
        assert printing is not None
        request = PrintExecutionRequest(
            uuid4(),
            bambu_3mf,
            material_bindings=(
                MaterialBinding(
                    material_index=0,
                    slot_id="bambu:unit:0:tray:0",
                    toolhead_id="bambu:toolhead:0",
                ),
            ),
        )
        await printing.submit(request)

        changed = replace(
            request,
            material_bindings=(
                MaterialBinding(
                    material_index=0,
                    slot_id="bambu:unit:0:tray:0",
                    toolhead_id="bambu:toolhead:1",
                ),
            ),
        )
        with pytest.raises(PrinterAdapterError) as caught:
            await printing.submit(changed)

        assert caught.value.code == PrinterErrorCode.CONFLICT
        assert fake_bambu_transport.submit_count == 1
        await adapter.disconnect()

    asyncio.run(scenario())
