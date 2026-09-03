# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Callable

from foxforge.domain.printers import PrinterId
from foxforge.domain.printers.capabilities import (
    MATERIAL_SYSTEM_CAPABILITY_ID,
    MATERIAL_SYSTEM_MAJOR_VERSION,
    MaterialSystemDescriptor,
    MaterialSystemSnapshot,
)

from .mapping import map_bambu_material_system
from .native import BambuNativeState


class BambuMaterialSystemCapability:
    """Expose Bambu AMS/external sources through the common observation contract."""

    def __init__(self, printer_id: PrinterId, native_snapshot: Callable[[], BambuNativeState]) -> None:
        self._printer_id = printer_id
        self._native_snapshot = native_snapshot
        self._descriptor = MaterialSystemDescriptor(
            capability_id=MATERIAL_SYSTEM_CAPABILITY_ID,
            major_version=MATERIAL_SYSTEM_MAJOR_VERSION,
            reports_active_source=True,
            reports_remaining_fraction=True,
            reports_material_identity=True,
            reports_tag_identity=True,
        )

    @property
    def descriptor(self) -> MaterialSystemDescriptor:
        return self._descriptor

    def snapshot(self) -> MaterialSystemSnapshot:
        return map_bambu_material_system(self._printer_id, self._native_snapshot())
