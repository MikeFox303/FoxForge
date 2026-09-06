# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import hashlib
import json
import zipfile
from collections.abc import Callable
from pathlib import Path

from foxforge.application.fleet import FleetService
from foxforge.application.queue import InMemoryQueueStore, QueueEntryState, QueueService
from foxforge.domain.printers import PrinterIdentity, utc_now
from foxforge.domain.printers.capabilities import (
    DetectedMaterial,
    LocalPrintArtifact,
    MaterialActivity,
    MaterialBinding,
    MaterialPresence,
    MaterialRouteKind,
    MaterialRouteSnapshot,
    MaterialSlotSnapshot,
    MaterialSystemCapability,
    MaterialSystemSnapshot,
    MaterialToolheadSnapshot,
    MaterialTopologyCapability,
    MaterialTopologySnapshot,
    MaterialUnitKind,
    MaterialUnitSnapshot,
    PrintArtifactFormat,
    PrintAssessmentBlockerCode,
    PrintExecutionCapability,
    PrintExecutionRequest,
)
from foxforge.testing import (
    FakeMaterialSystemCapability,
    FakeMaterialTopologyCapability,
    FakePrinterAdapter,
    FakePrintExecutionCapability,
)

_SLOT_ID = "source:slot-0"
_TOOLHEAD_0 = "toolhead-0"
_TOOLHEAD_1 = "toolhead-1"


class _ObservingPrintExecutionCapability(FakePrintExecutionCapability):
    def __init__(
        self,
        adapter: FakePrinterAdapter,
        on_assess: Callable[[PrintExecutionRequest], None],
    ) -> None:
        super().__init__(adapter)
        self._on_assess = on_assess

    async def assess(self, request: PrintExecutionRequest):
        self._on_assess(request)
        return await super().assess(request)


def test_assess_persists_compiled_toolhead_before_adapter_assessment(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        artifact = _three_mf_artifact(tmp_path / "routed.3mf")
        material = _material_snapshot(printer_identity.printer_id)
        topology = _topology_snapshot(printer_identity.printer_id)
        adapter = FakePrinterAdapter(printer_identity)
        store = InMemoryQueueStore()
        queue_id = None

        def observe(request: PrintExecutionRequest) -> None:
            assert request.material_bindings[0].toolhead_id == _TOOLHEAD_0
            assert queue_id is not None
            persisted = store.get(queue_id)
            assert persisted is not None
            assert persisted.request == request
            assert persisted.request.material_bindings[0].toolhead_id == _TOOLHEAD_0

        printing = _ObservingPrintExecutionCapability(adapter, observe)
        material_capability = FakeMaterialSystemCapability(adapter, material)
        topology_capability = FakeMaterialTopologyCapability(adapter, topology)
        adapter.register_capability(PrintExecutionCapability, printing)
        adapter.register_capability(MaterialSystemCapability, material_capability)
        adapter.register_capability(MaterialTopologyCapability, topology_capability)
        await adapter.connect()

        queue = QueueService(FleetService([adapter]), store)
        entry = queue.enqueue(
            printer_identity.printer_id,
            artifact,
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )
        queue_id = entry.queue_id

        assessed = await queue.assess(entry.queue_id)

        assert assessed.state == QueueEntryState.PENDING
        assert assessed.assessment is not None and assessed.assessment.eligible
        assert assessed.request.material_bindings == (MaterialBinding(0, _SLOT_ID, _TOOLHEAD_0),)
        assert printing.submit_attempt_count == 0
        assert printing.start_count == 0

    asyncio.run(scenario())


def test_dispatch_revalidates_persisted_route_and_blocks_changed_toolhead(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        artifact = _three_mf_artifact(tmp_path / "changed-route.3mf")
        material = _material_snapshot(printer_identity.printer_id)
        adapter = FakePrinterAdapter(printer_identity)
        printing = FakePrintExecutionCapability(adapter)
        material_capability = FakeMaterialSystemCapability(adapter, material)
        topology_capability = FakeMaterialTopologyCapability(
            adapter,
            _topology_snapshot(printer_identity.printer_id),
        )
        adapter.register_capability(PrintExecutionCapability, printing)
        adapter.register_capability(MaterialSystemCapability, material_capability)
        adapter.register_capability(MaterialTopologyCapability, topology_capability)
        await adapter.connect()

        queue = QueueService(FleetService([adapter]), InMemoryQueueStore())
        entry = queue.enqueue(
            printer_identity.printer_id,
            artifact,
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )
        assessed = await queue.assess(entry.queue_id)
        assert assessed.request.material_bindings[0].toolhead_id == _TOOLHEAD_0

        topology_capability.set_snapshot(
            MaterialTopologySnapshot(
                printer_id=printer_identity.printer_id,
                toolheads=(
                    MaterialToolheadSnapshot(_TOOLHEAD_0, "Left", 1),
                    MaterialToolheadSnapshot(_TOOLHEAD_1, "Right", 0),
                ),
                routes=(MaterialRouteSnapshot(_SLOT_ID, (_TOOLHEAD_1,), MaterialRouteKind.FIXED),),
                observed_at=utc_now(),
                stale=False,
            )
        )

        try:
            blocked = await queue.dispatch(entry.queue_id)
            assert blocked.state == QueueEntryState.BLOCKED
            assert blocked.assessment is not None
            assert not blocked.assessment.eligible
            assert blocked.assessment.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID
            assert blocked.request.material_bindings[0].toolhead_id == _TOOLHEAD_0
            assert printing.submit_attempt_count == 0
            assert printing.start_count == 0
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def test_routed_three_mf_blocks_when_live_material_capabilities_are_missing(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter = FakePrinterAdapter(printer_identity)
        printing = FakePrintExecutionCapability(adapter)
        adapter.register_capability(PrintExecutionCapability, printing)
        await adapter.connect()
        queue = QueueService(FleetService([adapter]), InMemoryQueueStore())
        entry = queue.enqueue(
            printer_identity.printer_id,
            _three_mf_artifact(tmp_path / "missing-capabilities.3mf"),
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )

        assessed = await queue.assess(entry.queue_id)

        assert assessed.state == QueueEntryState.BLOCKED
        assert assessed.assessment is not None
        assert assessed.assessment.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE
        assert printing.assess_count == 0
        assert printing.submit_attempt_count == 0

    asyncio.run(scenario())


def _three_mf_artifact(path: Path) -> LocalPrintArtifact:
    settings = {
        "filament_type": ["PETG"],
        "filament_colour": ["#FF6600"],
        "filament_settings_id": ["Test PETG"],
        "physical_extruder_map": [0, 1],
        "filament_nozzle_map": [0],
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/project_settings.config", json.dumps(settings))
        archive.writestr("Metadata/plate_1.gcode", "M620 S0A\nG1 X1 Y1\n")
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    return LocalPrintArtifact(
        artifact_id=digest,
        path=path.resolve(),
        filename=path.name,
        format=PrintArtifactFormat.THREE_MF,
        size_bytes=len(payload),
        sha256=digest,
    )


def _material_snapshot(printer_id: str) -> MaterialSystemSnapshot:
    slot = MaterialSlotSnapshot(
        slot_id=_SLOT_ID,
        unit_id="source:unit-0",
        position=0,
        label="Source 1",
        presence=MaterialPresence.LOADED,
        activity=MaterialActivity.INACTIVE,
        detected_material=DetectedMaterial(
            material_family="PETG",
            vendor_name="Test",
            product_name="PETG",
            color=None,
            tag=None,
            remaining_fraction=0.8,
        ),
    )
    return MaterialSystemSnapshot(
        printer_id=printer_id,
        units=(
            MaterialUnitSnapshot(
                unit_id="source:unit-0",
                kind=MaterialUnitKind.MULTI_SLOT,
                label="Sources",
                position=0,
                slots=(slot,),
            ),
        ),
        observed_at=utc_now(),
        stale=False,
    )


def _topology_snapshot(printer_id: str) -> MaterialTopologySnapshot:
    return MaterialTopologySnapshot(
        printer_id=printer_id,
        toolheads=(
            MaterialToolheadSnapshot(_TOOLHEAD_0, "Left", 0),
            MaterialToolheadSnapshot(_TOOLHEAD_1, "Right", 1),
        ),
        routes=(MaterialRouteSnapshot(_SLOT_ID, (_TOOLHEAD_0,), MaterialRouteKind.FIXED),),
        observed_at=utc_now(),
        stale=False,
    )
