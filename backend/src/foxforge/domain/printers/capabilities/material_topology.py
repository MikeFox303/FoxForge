# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from ..models import CapabilityDescriptor, MaterialSlotId, PrinterId, normalize_utc

MATERIAL_TOPOLOGY_CAPABILITY_ID = "foxforge.material_topology"
MATERIAL_TOPOLOGY_MAJOR_VERSION = 1


@dataclass(frozen=True, slots=True)
class MaterialTopologyDescriptor(CapabilityDescriptor):
    reports_dynamic_routes: bool

    def __post_init__(self) -> None:
        CapabilityDescriptor.__post_init__(self)
        if (
            self.capability_id != MATERIAL_TOPOLOGY_CAPABILITY_ID
            or self.major_version != MATERIAL_TOPOLOGY_MAJOR_VERSION
        ):
            raise ValueError("MaterialTopologyDescriptor must describe foxforge.material_topology v1")


class MaterialRouteKind(StrEnum):
    FIXED = "fixed"
    DYNAMIC = "dynamic"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MaterialToolheadSnapshot:
    toolhead_id: str
    label: str | None
    position: int

    def __post_init__(self) -> None:
        if not self.toolhead_id:
            raise ValueError("toolhead_id must not be empty")
        if self.position < 0:
            raise ValueError("toolhead position must be non-negative")


@dataclass(frozen=True, slots=True)
class MaterialRouteSnapshot:
    source_slot_id: MaterialSlotId
    toolhead_ids: tuple[str, ...]
    kind: MaterialRouteKind

    def __post_init__(self) -> None:
        if not self.source_slot_id:
            raise ValueError("source_slot_id must not be empty")
        if len(self.toolhead_ids) != len(set(self.toolhead_ids)):
            raise ValueError("toolhead_ids must be unique within a material route")
        if any(not toolhead_id for toolhead_id in self.toolhead_ids):
            raise ValueError("material route toolhead ids must not be empty")
        if self.kind == MaterialRouteKind.FIXED and len(self.toolhead_ids) != 1:
            raise ValueError("fixed material routes must name exactly one toolhead")
        if self.kind == MaterialRouteKind.DYNAMIC and not self.toolhead_ids:
            raise ValueError("dynamic material routes must name at least one reachable toolhead")


@dataclass(frozen=True, slots=True)
class MaterialTopologySnapshot:
    printer_id: PrinterId
    toolheads: tuple[MaterialToolheadSnapshot, ...]
    routes: tuple[MaterialRouteSnapshot, ...]
    observed_at: datetime
    stale: bool

    def __post_init__(self) -> None:
        if not self.printer_id:
            raise ValueError("printer_id must not be empty")
        toolhead_ids = [toolhead.toolhead_id for toolhead in self.toolheads]
        if len(toolhead_ids) != len(set(toolhead_ids)):
            raise ValueError("material topology toolhead ids must be unique")
        source_ids = [route.source_slot_id for route in self.routes]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("material topology may report only one route per source slot")
        known_toolheads = set(toolhead_ids)
        if any(toolhead_id not in known_toolheads for route in self.routes for toolhead_id in route.toolhead_ids):
            raise ValueError("material routes may reference only toolheads present in the snapshot")
        object.__setattr__(self, "observed_at", normalize_utc(self.observed_at, field_name="observed_at"))


class MaterialTopologyCapability(Protocol):
    @property
    def descriptor(self) -> MaterialTopologyDescriptor: ...

    def snapshot(self) -> MaterialTopologySnapshot: ...
