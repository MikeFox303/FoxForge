# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import pytest

from foxforge.domain.printers import utc_now
from foxforge.domain.printers.capabilities import (
    MATERIAL_TOPOLOGY_CAPABILITY_ID,
    MATERIAL_TOPOLOGY_MAJOR_VERSION,
    MaterialRouteKind,
    MaterialRouteSnapshot,
    MaterialToolheadSnapshot,
    MaterialTopologyDescriptor,
    MaterialTopologySnapshot,
)


def test_material_topology_descriptor_identity_is_fixed() -> None:
    descriptor = MaterialTopologyDescriptor(
        capability_id=MATERIAL_TOPOLOGY_CAPABILITY_ID,
        major_version=MATERIAL_TOPOLOGY_MAJOR_VERSION,
        reports_dynamic_routes=True,
    )

    assert descriptor.capability_id == "foxforge.material_topology"
    assert descriptor.major_version == 1
    assert descriptor.reports_dynamic_routes is True


def test_fixed_route_requires_exactly_one_toolhead() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        MaterialRouteSnapshot(
            source_slot_id="slot-a",
            toolhead_ids=(),
            kind=MaterialRouteKind.FIXED,
        )

    with pytest.raises(ValueError, match="exactly one"):
        MaterialRouteSnapshot(
            source_slot_id="slot-a",
            toolhead_ids=("tool-a", "tool-b"),
            kind=MaterialRouteKind.FIXED,
        )


def test_dynamic_route_requires_reachable_toolhead_set() -> None:
    with pytest.raises(ValueError, match="at least one"):
        MaterialRouteSnapshot(
            source_slot_id="slot-a",
            toolhead_ids=(),
            kind=MaterialRouteKind.DYNAMIC,
        )


def test_unknown_route_can_be_explicit_without_guessing_target() -> None:
    route = MaterialRouteSnapshot(
        source_slot_id="slot-a",
        toolhead_ids=(),
        kind=MaterialRouteKind.UNKNOWN,
    )

    assert route.toolhead_ids == ()
    assert route.kind == MaterialRouteKind.UNKNOWN


def test_snapshot_rejects_routes_to_unknown_toolheads() -> None:
    with pytest.raises(ValueError, match="only toolheads present"):
        MaterialTopologySnapshot(
            printer_id="printer-1",
            toolheads=(MaterialToolheadSnapshot(toolhead_id="tool-a", label="A", position=0),),
            routes=(
                MaterialRouteSnapshot(
                    source_slot_id="slot-a",
                    toolhead_ids=("tool-b",),
                    kind=MaterialRouteKind.FIXED,
                ),
            ),
            observed_at=utc_now(),
            stale=False,
        )


def test_snapshot_rejects_duplicate_source_routes() -> None:
    with pytest.raises(ValueError, match="one route per source"):
        MaterialTopologySnapshot(
            printer_id="printer-1",
            toolheads=(MaterialToolheadSnapshot(toolhead_id="tool-a", label="A", position=0),),
            routes=(
                MaterialRouteSnapshot(
                    source_slot_id="slot-a",
                    toolhead_ids=("tool-a",),
                    kind=MaterialRouteKind.FIXED,
                ),
                MaterialRouteSnapshot(
                    source_slot_id="slot-a",
                    toolhead_ids=(),
                    kind=MaterialRouteKind.UNKNOWN,
                ),
            ),
            observed_at=utc_now(),
            stale=False,
        )
