# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from decimal import Decimal

import pytest

from foxforge.application.inventory import InMemoryInventoryStore, InventoryService, SpoolAssignmentConflictError


def test_move_spool_replaces_assignment_without_unassign_step() -> None:
    inventory = InventoryService(InMemoryInventoryStore())
    first = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal("1000"))
    second = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("1000"))

    inventory.assign_spool(first.spool_id, "x2d", "ams:0:0")
    moved = inventory.move_spool(first.spool_id, "x2d", "ams:0:1")

    assert moved.slot_id == "ams:0:1"
    assert inventory.assignment_for_spool(first.spool_id) == moved
    assert inventory.assignment_for_slot("x2d", "ams:0:0") is None

    inventory.assign_spool(second.spool_id, "x2d", "ams:0:2")
    with pytest.raises(SpoolAssignmentConflictError):
        inventory.move_spool(first.spool_id, "x2d", "ams:0:2")

    assert inventory.assignment_for_spool(first.spool_id) == moved
