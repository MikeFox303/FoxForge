# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from decimal import Decimal

import pytest

from foxforge.application.inventory import (
    ArchivedSpoolError,
    InMemoryInventoryStore,
    InventoryBalanceError,
    InventoryIdempotencyConflictError,
    InventoryService,
    SpoolAssignmentConflictError,
)
from foxforge.domain.inventory import SpoolAdjustmentKind, SpoolColor


def _service() -> InventoryService:
    return InventoryService(InMemoryInventoryStore())


def test_spool_balance_uses_immutable_idempotent_adjustment_ledger() -> None:
    inventory = _service()
    spool = inventory.add_spool(
        material_family="PETG",
        initial_filament_mass_g=Decimal("1000"),
        manufacturer="SUNLU",
        product_name="PETG",
        color=SpoolColor("112233FF"),
        empty_spool_mass_g=Decimal("190"),
    )

    first = inventory.consume(
        spool.spool_id,
        Decimal("14.5"),
        idempotency_key="queue:abc:spool:1",
        note="completed print",
    )
    replay = inventory.consume(
        spool.spool_id,
        Decimal("14.5"),
        idempotency_key="queue:abc:spool:1",
        note="completed print",
    )

    assert replay == first
    assert len(inventory.adjustments(spool.spool_id)) == 1
    balance = inventory.balance(spool.spool_id)
    assert balance.remaining_filament_mass_g == Decimal("985.5")
    assert balance.used_filament_mass_g == Decimal("14.5")
    assert balance.used_fraction == Decimal("0.0145")


def test_idempotency_key_reuse_with_different_adjustment_is_rejected() -> None:
    inventory = _service()
    first = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("1000"))
    second = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("1000"))

    inventory.consume(first.spool_id, Decimal("10"), idempotency_key="print:1")

    with pytest.raises(InventoryIdempotencyConflictError, match="different data"):
        inventory.consume(first.spool_id, Decimal("11"), idempotency_key="print:1")
    with pytest.raises(InventoryIdempotencyConflictError, match="different data"):
        inventory.consume(second.spool_id, Decimal("10"), idempotency_key="print:1")


def test_balance_cannot_drop_below_zero_or_exceed_initial_mass() -> None:
    inventory = _service()
    spool = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("100"))

    with pytest.raises(InventoryBalanceError, match="negative"):
        inventory.consume(spool.spool_id, Decimal("101"), idempotency_key="too-much")

    inventory.consume(spool.spool_id, Decimal("20"), idempotency_key="consume:20")
    inventory.return_material(spool.spool_id, Decimal("10"), idempotency_key="return:10")
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("90")

    with pytest.raises(InventoryBalanceError, match="initial"):
        inventory.return_material(spool.spool_id, Decimal("11"), idempotency_key="return:too-much")


def test_manual_correction_by_delta_is_audited_and_idempotent() -> None:
    inventory = _service()
    spool = inventory.add_spool(material_family="TPU", initial_filament_mass_g=Decimal("750"))
    inventory.consume(spool.spool_id, Decimal("50"), idempotency_key="print:1")

    correction = inventory.correct_by_delta(
        spool.spool_id,
        Decimal("5.5"),
        idempotency_key="manual:scale:1",
        note="weighed spool",
    )
    replay = inventory.correct_by_delta(
        spool.spool_id,
        Decimal("5.5"),
        idempotency_key="manual:scale:1",
        note="weighed spool",
    )

    assert correction.kind == SpoolAdjustmentKind.CORRECTION
    assert replay == correction
    assert inventory.balance(spool.spool_id).remaining_filament_mass_g == Decimal("705.5")


def test_empty_spool_weight_is_editable_after_creation() -> None:
    inventory = _service()
    spool = inventory.add_spool(
        material_family="PLA",
        initial_filament_mass_g=Decimal("1000"),
        empty_spool_mass_g=None,
    )

    updated = inventory.set_empty_spool_mass(spool.spool_id, Decimal("184.7"))
    assert updated.empty_spool_mass_g == Decimal("184.7")
    assert inventory.get_spool(spool.spool_id).empty_spool_mass_g == Decimal("184.7")


def test_assignments_keep_spool_identity_outside_printer_adapter_state() -> None:
    inventory = _service()
    first = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal("1000"))
    second = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("1000"))
    slot_id = "bambu:unit:0:tray:1"

    assignment = inventory.assign_spool(first.spool_id, "x2d-main", slot_id)
    assert assignment.spool_id == first.spool_id
    assert assignment.printer_id == "x2d-main"
    assert assignment.slot_id == slot_id
    assert inventory.assignment_for_slot("x2d-main", slot_id) == assignment
    assert inventory.assignment_for_spool(first.spool_id) == assignment

    assert inventory.assign_spool(first.spool_id, "x2d-main", slot_id) == assignment

    with pytest.raises(SpoolAssignmentConflictError, match="another spool"):
        inventory.assign_spool(second.spool_id, "x2d-main", slot_id)
    with pytest.raises(SpoolAssignmentConflictError, match="unassign"):
        inventory.assign_spool(first.spool_id, "ender-ke", "moonraker:external")

    removed = inventory.unassign_spool(first.spool_id)
    assert removed == assignment
    moved = inventory.assign_spool(first.spool_id, "ender-ke", "moonraker:external")
    assert moved.printer_id == "ender-ke"


def test_assigned_spool_must_be_unassigned_before_archive() -> None:
    inventory = _service()
    spool = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("1000"))
    inventory.assign_spool(spool.spool_id, "printer-1", "slot-1")

    with pytest.raises(SpoolAssignmentConflictError, match="unassigned"):
        inventory.archive_spool(spool.spool_id)

    inventory.unassign_spool(spool.spool_id)
    archived = inventory.archive_spool(spool.spool_id)
    assert archived.archived is True
    assert inventory.list_spools() == ()
    assert inventory.list_spools(include_archived=True) == (archived,)

    with pytest.raises(ArchivedSpoolError, match="assigned"):
        inventory.assign_spool(spool.spool_id, "printer-1", "slot-1")
    with pytest.raises(ArchivedSpoolError, match="adjustments"):
        inventory.consume(spool.spool_id, Decimal("1"), idempotency_key="after-archive")
