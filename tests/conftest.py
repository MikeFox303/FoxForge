# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from foxforge.domain.printers import PrinterIdentity, utc_now
from foxforge.domain.printers.capabilities import (
    DetectedMaterial,
    LocalPrintArtifact,
    MaterialActivity,
    MaterialColor,
    MaterialPresence,
    MaterialSlotSnapshot,
    MaterialSystemSnapshot,
    MaterialTagIdentity,
    MaterialUnitKind,
    MaterialUnitSnapshot,
    PrintArtifactFormat,
)


@pytest.fixture
def printer_identity() -> PrinterIdentity:
    return PrinterIdentity(
        printer_id="printer-1",
        display_name="Contract Printer",
        vendor="test_vendor",
        model="TEST-1",
        serial_number="TEST123",
        adapter_kind="fake",
    )


@pytest.fixture
def material_snapshot() -> MaterialSystemSnapshot:
    loaded = MaterialSlotSnapshot(
        slot_id="opaque:unit-a:slot-0",
        unit_id="opaque:unit-a",
        position=0,
        label="Slot A",
        presence=MaterialPresence.LOADED,
        activity=MaterialActivity.INACTIVE,
        detected_material=DetectedMaterial(
            material_family="PETG",
            vendor_name="Test Filament",
            product_name="PETG",
            color=MaterialColor("FF6600FF"),
            tag=MaterialTagIdentity(scheme="test-rfid", value="tag-123"),
            remaining_fraction=0.75,
        ),
    )
    empty = MaterialSlotSnapshot(
        slot_id="opaque:unit-a:slot-1",
        unit_id="opaque:unit-a",
        position=1,
        label="Slot B",
        presence=MaterialPresence.EMPTY,
        activity=MaterialActivity.INACTIVE,
        detected_material=None,
    )
    return MaterialSystemSnapshot(
        printer_id="printer-1",
        units=(
            MaterialUnitSnapshot(
                unit_id="opaque:unit-a",
                kind=MaterialUnitKind.MULTI_SLOT,
                label="Test multi-slot source",
                position=0,
                slots=(loaded, empty),
            ),
        ),
        observed_at=utc_now(),
        stale=False,
    )


def make_artifact(
    path: Path,
    *,
    artifact_format: PrintArtifactFormat = PrintArtifactFormat.GCODE,
) -> LocalPrintArtifact:
    payload = b"G28\nG1 X10 Y10\n"
    path.write_bytes(payload)
    return LocalPrintArtifact(
        artifact_id="artifact-1",
        path=path.resolve(),
        filename=path.name,
        format=artifact_format,
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
