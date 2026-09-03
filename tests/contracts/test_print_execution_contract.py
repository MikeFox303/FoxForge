# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest

from foxforge.domain.printers import OperationalState, PrinterAdapterError, PrinterErrorCode
from foxforge.domain.printers.capabilities import (
    MaterialBinding,
    PrintArtifactFormat,
    PrintArtifactSelection,
    PrintAssessmentBlockerCode,
    PrintExecutionRequest,
)
from foxforge.testing import build_fake_printer
from tests.helpers import make_artifact


def test_assess_is_side_effect_free_and_validates_ready_request(tmp_path, printer_identity, material_snapshot) -> None:
    async def scenario() -> None:
        adapter, printing, _material = build_fake_printer(printer_identity, material_snapshot=material_snapshot)
        await adapter.connect()
        artifact = make_artifact(tmp_path / "job.gcode")
        request = PrintExecutionRequest(
            dispatch_id=uuid4(),
            artifact=artifact,
            material_bindings=(MaterialBinding(0, "opaque:unit-a:slot-0"),),
        )
        before = adapter.snapshot()

        assessment = await printing.assess(request)

        assert assessment.eligible
        assert assessment.blockers == ()
        assert printing.start_count == 0
        assert adapter.snapshot() == before

    asyncio.run(scenario())


def test_assess_blocks_unsupported_format(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(
            printer_identity,
            accepted_formats=frozenset({PrintArtifactFormat.GCODE}),
            supports_material_bindings=False,
        )
        await adapter.connect()
        artifact = make_artifact(tmp_path / "job.3mf", artifact_format=PrintArtifactFormat.THREE_MF)
        assessment = await printing.assess(PrintExecutionRequest(uuid4(), artifact))

        assert not assessment.eligible
        assert PrintAssessmentBlockerCode.UNSUPPORTED_ARTIFACT in {blocker.code for blocker in assessment.blockers}
        assert printing.start_count == 0

    asyncio.run(scenario())


def test_assess_blocks_unsupported_plate_selection(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(
            printer_identity,
            supports_plate_selection=False,
            supports_material_bindings=False,
        )
        await adapter.connect()
        artifact = make_artifact(tmp_path / "job.gcode")
        request = PrintExecutionRequest(uuid4(), artifact, selection=PrintArtifactSelection(plate_index=0))
        assessment = await printing.assess(request)

        assert PrintAssessmentBlockerCode.UNSUPPORTED_SELECTION in {blocker.code for blocker in assessment.blockers}

    asyncio.run(scenario())


def test_invalid_material_slot_is_rejected_without_vendor_types(tmp_path, printer_identity, material_snapshot) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, material_snapshot=material_snapshot)
        await adapter.connect()
        artifact = make_artifact(tmp_path / "job.gcode")
        request = PrintExecutionRequest(
            uuid4(),
            artifact,
            material_bindings=(MaterialBinding(0, "not-a-real-slot"),),
        )
        assessment = await printing.assess(request)
        assert PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID in {blocker.code for blocker in assessment.blockers}

        with pytest.raises(PrinterAdapterError) as caught:
            await printing.submit(request)
        assert caught.value.code == PrinterErrorCode.INVALID_REQUEST
        assert caught.value.vendor_code is None

    asyncio.run(scenario())


def test_same_dispatch_and_fingerprint_is_idempotent(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        artifact = make_artifact(tmp_path / "job.gcode")
        request = PrintExecutionRequest(uuid4(), artifact, requested_name="same job")

        first = await printing.submit(request)
        second = await printing.submit(request)

        assert second == first
        assert printing.start_count == 1
        assert printing.submit_attempt_count == 2
        assert adapter.snapshot().operational_state == OperationalState.PREPARING

    asyncio.run(scenario())


def test_dispatch_id_reuse_with_different_request_conflicts(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        artifact = make_artifact(tmp_path / "job.gcode")
        dispatch_id = uuid4()
        request = PrintExecutionRequest(dispatch_id, artifact, requested_name="first")
        await printing.submit(request)

        changed = replace(request, requested_name="different")
        with pytest.raises(PrinterAdapterError) as caught:
            await printing.submit(changed)
        assert caught.value.code == PrinterErrorCode.CONFLICT
        assert not caught.value.retryable
        assert printing.start_count == 1

    asyncio.run(scenario())


def test_indeterminate_submission_requires_reconciliation_before_retry(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        artifact = make_artifact(tmp_path / "job.gcode")
        request = PrintExecutionRequest(uuid4(), artifact)
        printing.make_next_submit_indeterminate()

        with pytest.raises(PrinterAdapterError) as first:
            await printing.submit(request)
        assert first.value.code == PrinterErrorCode.INDETERMINATE
        assert printing.start_count == 1

        with pytest.raises(PrinterAdapterError) as second:
            await printing.submit(request)
        assert second.value.code == PrinterErrorCode.INDETERMINATE
        assert printing.start_count == 1

        receipt = printing.resolve_indeterminate(request.dispatch_id, accepted=True)
        assert receipt is not None
        assert await printing.submit(request) == receipt
        assert printing.start_count == 1

    asyncio.run(scenario())


def test_fake_can_simulate_transport_delay_without_transport_knowledge(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        printing.submit_delay_seconds = 0.001
        await adapter.connect()
        artifact = make_artifact(tmp_path / "job.gcode")
        receipt = await printing.submit(PrintExecutionRequest(uuid4(), artifact))
        assert receipt.vendor_job_id and receipt.vendor_job_id.startswith("fake:")

    asyncio.run(scenario())
