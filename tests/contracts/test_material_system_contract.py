# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import fields, replace

from foxforge.domain.printers import PrinterEventKind, utc_now
from foxforge.domain.printers.capabilities import (
    MATERIAL_SYSTEM_CAPABILITY_ID,
    MATERIAL_SYSTEM_MAJOR_VERSION,
    MaterialSystemCapability,
)
from foxforge.testing import FakeMaterialSystemCapability, FakePrinterAdapter


def test_material_descriptor_and_snapshot_are_vendor_neutral(printer_identity, material_snapshot) -> None:
    adapter = FakePrinterAdapter(printer_identity)
    capability = FakeMaterialSystemCapability(adapter, material_snapshot)
    adapter.register_capability(MaterialSystemCapability, capability)

    assert capability.descriptor.capability_id == MATERIAL_SYSTEM_CAPABILITY_ID
    assert capability.descriptor.major_version == MATERIAL_SYSTEM_MAJOR_VERSION
    assert capability.snapshot() is material_snapshot
    assert adapter.capability(MaterialSystemCapability) is capability

    slot = material_snapshot.units[0].slots[0]
    assert slot.slot_id == "opaque:unit-a:slot-0"
    assert "spool_id" not in {field.name for field in fields(slot)}
    assert "ams" not in {field.name.lower() for field in fields(slot)}


def test_material_snapshot_update_emits_normalized_event(printer_identity, material_snapshot) -> None:
    async def scenario() -> None:
        adapter = FakePrinterAdapter(printer_identity)
        capability = FakeMaterialSystemCapability(adapter, material_snapshot)
        adapter.register_capability(MaterialSystemCapability, capability)
        await adapter.connect()
        events = adapter.events()
        try:
            updated = replace(material_snapshot, observed_at=utc_now(), stale=True)
            capability.set_snapshot(updated)
            event = await asyncio.wait_for(anext(events), timeout=0.1)
            assert event.kind == PrinterEventKind.MATERIAL_SYSTEM_CHANGED
            assert event.payload == updated
        finally:
            await events.aclose()  # type: ignore[attr-defined]

    asyncio.run(scenario())
