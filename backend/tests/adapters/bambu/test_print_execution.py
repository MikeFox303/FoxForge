# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest

from foxforge.adapters.bambu import BambuAdapter, BambuTransportError, BambuTransportErrorKind
from foxforge.domain.printers import PrinterAdapterError, PrinterErrorCode
from foxforge.domain.printers.capabilities import (
    MaterialBinding,
    PrintArtifactSelection,
    PrintAssessmentBlockerCode,
    PrintExecutionCapability,
    PrintExecutionRequest,
)


def test_bambu_dispatch_translates_compiled_plate_material_and_nozzle_routes(
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
            dispatch_id=uuid4(),
            artifact=bambu_3mf,
            selection=PrintArtifactSelection(plate_index=0),
            material_bindings=(
                MaterialBinding(
                    material_index=0,
                    slot_id="bambu:unit:0:tray:0",
                    toolhead_id="bambu:toolhead:0",
                ),
                MaterialBinding(
                    material_index=1,
                    slot_id="bambu:unit:0:tray:1",
                    toolhead_id="bambu:toolhead:0",
                ),
            ),
            requested_name="PETG with support",
        )

        assessment = await printing.assess(request)
        receipt = await printing.submit(request)

        assert assessment.eligible
        assert receipt.dispatch_id == request.dispatch_id
        assert fake_bambu_transport.submit_count == 1
        native = fake_bambu_transport.submitted[0]
        assert native.plate_number == 1
        assert [
            (route.material_index, route.ams_id, route.tray_id, route.nozzle_index)
            for route in native.material_routes
        ] == [
            (0, 0, 0, 0),
            (1, 0, 1, 0),
        ]
        await adapter.disconnect()

    asyncio.run(scenario())


def test_bambu_material_binding_requires_compiler_owned_toolhead(
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
            material_bindings=(MaterialBinding(0, "bambu:unit:0:tray:0"),),
        )

        assessment = await printing.assess(request)

        assert not assessment.eligible
        assert assessment.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID
        with pytest.raises(PrinterAdapterError) as caught:
            await printing.submit(request)
        assert caught.value.code == PrinterErrorCode.INVALID_REQUEST
        assert fake_bambu_transport.submit_count == 0
        await adapter.disconnect()

    asyncio.run(scenario())


def test_bambu_revalidates_compiled_toolhead_against_current_native_topology(
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
                    0,
                    "bambu:unit:0:tray:0",
                    "bambu:toolhead:1",
                ),
            ),
        )

        assessment = await printing.assess(request)

        assert not assessment.eligible
        assert assessment.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID
        with pytest.raises(PrinterAdapterError) as caught:
            await printing.submit(request)
        assert caught.value.code == PrinterErrorCode.INVALID_REQUEST
        assert fake_bambu_transport.submit_count == 0
        await adapter.disconnect()

    asyncio.run(scenario())


def test_confirmed_bambu_dispatch_is_idempotent(bambu_identity, fake_bambu_transport, bambu_3mf) -> None:
    async def scenario() -> None:
        adapter = BambuAdapter(bambu_identity, fake_bambu_transport)
        await adapter.connect()
        printing = adapter.capability(PrintExecutionCapability)
        assert printing is not None
        request = PrintExecutionRequest(uuid4(), bambu_3mf)

        first = await printing.submit(request)
        second = await printing.submit(request)

        assert second == first
        assert fake_bambu_transport.submit_count == 1
        await adapter.disconnect()

    asyncio.run(scenario())


def test_dispatch_id_reuse_with_changed_bambu_request_conflicts(
    bambu_identity,
    fake_bambu_transport,
    bambu_3mf,
) -> None:
    async def scenario() -> None:
        adapter = BambuAdapter(bambu_identity, fake_bambu_transport)
        await adapter.connect()
        printing = adapter.capability(PrintExecutionCapability)
        assert printing is not None
        request = PrintExecutionRequest(uuid4(), bambu_3mf, requested_name="first")
        await printing.submit(request)

        with pytest.raises(PrinterAdapterError) as caught:
            await printing.submit(replace(request, requested_name="changed"))
        assert caught.value.code == PrinterErrorCode.CONFLICT
        assert fake_bambu_transport.submit_count == 1
        await adapter.disconnect()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("transport_kind", "expected_code", "retryable"),
    [
        (BambuTransportErrorKind.UNAVAILABLE, PrinterErrorCode.CONNECTION_UNAVAILABLE, True),
        (BambuTransportErrorKind.AUTHENTICATION, PrinterErrorCode.AUTHENTICATION_FAILED, False),
        (BambuTransportErrorKind.TIMEOUT, PrinterErrorCode.TIMEOUT, True),
        (BambuTransportErrorKind.BUSY, PrinterErrorCode.BUSY, True),
        (BambuTransportErrorKind.REJECTED, PrinterErrorCode.REMOTE_REJECTED, False),
        (BambuTransportErrorKind.INDETERMINATE, PrinterErrorCode.INDETERMINATE, False),
        (BambuTransportErrorKind.INTERNAL, PrinterErrorCode.INTERNAL_ADAPTER_ERROR, False),
    ],
)
def test_bambu_transport_errors_are_normalized(
    bambu_identity,
    fake_bambu_transport,
    bambu_3mf,
    transport_kind,
    expected_code,
    retryable,
) -> None:
    async def scenario() -> None:
        adapter = BambuAdapter(bambu_identity, fake_bambu_transport)
        await adapter.connect()
        printing = adapter.capability(PrintExecutionCapability)
        assert printing is not None
        fake_bambu_transport.next_submit_error = BambuTransportError(
            transport_kind,
            "vendor failure",
            vendor_code="BAMBU_TEST",
        )

        with pytest.raises(PrinterAdapterError) as caught:
            await printing.submit(PrintExecutionRequest(uuid4(), bambu_3mf))

        assert caught.value.code == expected_code
        assert caught.value.retryable is retryable
        assert caught.value.vendor_code == "BAMBU_TEST"
        await adapter.disconnect()

    asyncio.run(scenario())
