# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Callable

from foxforge.domain.printers.capabilities import (
    MATERIAL_SYSTEM_CAPABILITY_ID,
    MATERIAL_SYSTEM_MAJOR_VERSION,
    MaterialSystemDescriptor,
    MaterialSystemSnapshot,
)

from .mapping import map_moonraker_material_system
from .native import MoonrakerNativeState


class MoonrakerMaterialSystemCapability:
    """Expose a generic external material source for Moonraker printers."""

    def __init__(self, printer_id: str, native_snapshot: Callable[[], MoonrakerNativeState]) -> None:
        self._printer_id = printer_id
        self._native_snapshot = native_snapshot
        self._descriptor = MaterialSystemDescriptor(
            capability_id=MATERIAL_SYSTEM_CAPABILITY_ID,
            major_version=MATERIAL_SYSTEM_MAJOR_VERSION,
            reports_active_source=False,
            reports_remaining_fraction=False,
            reports_material_identity=False,
            reports_tag_identity=False,
        )

    @property
    def descriptor(self) -> MaterialSystemDescriptor:
        return self._descriptor

    def snapshot(self) -> MaterialSystemSnapshot:
        return map_moonraker_material_system(self._printer_id, self._native_snapshot())
