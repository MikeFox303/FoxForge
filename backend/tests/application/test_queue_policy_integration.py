# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from foxforge.application.fleet import FleetService
from foxforge.application.queue import (
    InMemoryQueueStore,
    QueueDispatchGateResult,
    QueueEntry,
    QueueEntryState,
    QueueService,
)
from foxforge.domain.printers import ActiveJobSnapshot, JobState, OperationalState, utc_now
from foxforge.domain.printers.capabilities import (
    DetectedMaterial,
    LocalPrintArtifact,
    MaterialActivity,
    MaterialBinding,
    MaterialPresence,
    MaterialRouteKind,
    MaterialRouteSnapshot,
    MaterialSlotSnapshot,
    MaterialSystemSnapshot,
    MaterialToolheadSnapshot,
    MaterialTopologySnapshot,
    MaterialUnitKind,
    MaterialUnitSnapshot,
    PrintArtifactFormat,
    PrintAssessmentBlocker,
    PrintAssessmentBlockerCode,
)
from foxforge.testing import FakePrintExecutionCapability, build_fake_printer
from tests.helpers import make_artifact

_SLOT_ID = "source:slot-0"
_TOOLHEAD_ID = "toolhead-0"


@dataclass
class _RecordingGate:
    store: InMemoryQueueStore
    printing: FakePrintExecutionCapability
    blocker: PrintAssessmentBlocker | None = None
    seen: QueueEntry | None = None

    def assess_dispatch(self, entry: QueueEntry) -> QueueDispatchGateResult:
        persisted = self.store.get(entry.queue_id)
        assert persisted is not None
        assert persisted.state == QueueEntryState.PENDING
        assert persisted.request == entry.request
        assert self.printing.submit_attempt_count == 0
        self.seen = entry
        if self.blocker is None:
            return QueueDispatchGateResult()
        return QueueDispatchGateResult((self.blocker,))


class _ExplodingObserver:
    def __init__(self) -> None:
        self.calls = 0

    def sync_queue_entry(self, entry: QueueEntry) -> object:
        self.calls += 1
        raise RuntimeError(f"observer failed for {entry.state.value}")


async def _wait_for_state(queue: QueueService, queue_id, state: QueueEntryState) -> None:
    for _ in range(100):
        if queue.get(queue_id).state == state:
            return
        await asyncio.sleep(0.005)
    assert queue.get(queue_id).state == state


def test_pre_dispatch_gate_blocks_before_durable_start_boundary(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        store = InMemoryQueueStore()
        gate = _RecordingGate(
            store,
            printing,
            PrintAssessmentBlocker(
                PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                "policy blocker",
            ),
        )
        queue = QueueService(FleetService([adapter]), store, pre_dispatch_gate=gate)
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "blocked.gcode"))

        try:
            blocked = await queue.dispatch(entry.queue_id)
            assert gate.seen is not None
            assert blocked.state == QueueEntryState.BLOCKED
            assert blocked.attempt_count == 0
            assert blocked.last_attempt_at is None
            assert printing.submit_attempt_count == 0
            assert printing.start_count == 0
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def test_gate_sees_fresh_compiler_owned_route_before_submit(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, printing, _ = build_fake_printer(
            printer_identity,
            material_snapshot=_material_snapshot(printer_identity.printer_id),
            material_topology_snapshot=_topology_snapshot(printer_identity.printer_id),
        )
        await adapter.connect()
        store = InMemoryQueueStore()
        gate = _RecordingGate(store, printing)
        queue = QueueService(FleetService([adapter]), store, pre_dispatch_gate=gate)
        entry = queue.enqueue(
            printer_identity.printer_id,
            _three_mf_artifact(tmp_path / "routed.3mf"),
            material_bindings=(MaterialBinding(0, _SLOT_ID),),
        )

        try:
            accepted = await queue.dispatch(entry.queue_id)
            assert accepted.state == QueueEntryState.ACCEPTED
            assert gate.seen is not None
            assert gate.seen.assessment is not None and gate.seen.assessment.eligible
            assert gate.seen.request.material_bindings == (MaterialBinding(0, _SLOT_ID, _TOOLHEAD_ID),)
            assert printing.start_count == 1
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def test_lifecycle_observer_failure_does_not_stop_queue_event_tracking(tmp_path, printer_identity) -> None:
    async def scenario() -> None:
        adapter, _, _ = build_fake_printer(printer_identity, supports_material_bindings=False)
        await adapter.connect()
        observer = _ExplodingObserver()
        queue = QueueService(
            FleetService([adapter]),
            InMemoryQueueStore(),
            lifecycle_observer=observer,
        )
        entry = queue.enqueue(printer_identity.printer_id, make_artifact(tmp_path / "observer.gcode"))

        try:
            accepted = await queue.dispatch(entry.queue_id)
            assert accepted.receipt is not None and accepted.receipt.vendor_job_id is not None
            adapter.set_active_job(
                _job(accepted.receipt.vendor_job_id, JobState.COMPLETED),
                operational_state=OperationalState.COMPLETED,
            )
            await _wait_for_state(queue, entry.queue_id, QueueEntryState.COMPLETED)
            assert observer.calls > 0
        finally:
            await queue.aclose()

    asyncio.run(scenario())


def _job(vendor_job_id: str, state: JobState) -> ActiveJobSnapshot:
    return ActiveJobSnapshot(
        vendor_job_id=vendor_job_id,
        name="policy.gcode",
        state=state,
        progress=1.0 if state == JobState.COMPLETED else None,
        elapsed_seconds=None,
        remaining_seconds=None,
        current_layer=None,
        total_layers=None,
    )


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
        toolheads=(MaterialToolheadSnapshot(_TOOLHEAD_ID, "Left", 0),),
        routes=(MaterialRouteSnapshot(_SLOT_ID, (_TOOLHEAD_ID,), MaterialRouteKind.FIXED),),
        observed_at=utc_now(),
        stale=False,
    )
