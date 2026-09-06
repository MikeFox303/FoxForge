# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace
from uuid import uuid4

from foxforge.adapters.bambu.mapping import map_bambu_state
from foxforge.adapters.bambu.print_execution import BambuPrintExecutionCapability
from foxforge.domain.printers import utc_now
from foxforge.domain.printers.capabilities import MaterialBinding, PrintExecutionRequest


def test_submit_uses_one_native_snapshot_for_revalidation_and_request_construction(
    bambu_identity,
    fake_bambu_transport,
    bambu_3mf,
) -> None:
    async def scenario() -> None:
        first = replace(fake_bambu_transport.snapshot(), connected=True, observed_at=utc_now())
        second = replace(
            first,
            material_units=(replace(first.material_units[0], routed_extruder_id=1),),
            observed_at=utc_now(),
        )
        calls = 0

        def native_snapshot():
            nonlocal calls
            calls += 1
            return first if calls == 1 else second

        printing = BambuPrintExecutionCapability(
            fake_bambu_transport,
            lambda: map_bambu_state(bambu_identity.printer_id, first),
            native_snapshot,
        )
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

        assert calls == 1
        assert fake_bambu_transport.submit_count == 1
        assert fake_bambu_transport.submitted[0].material_routes[0].nozzle_index == 0

    asyncio.run(scenario())
