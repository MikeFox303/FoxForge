# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from foxforge.application.inventory import (
    ArchivedSpoolError,
    InventoryIdempotencyConflictError,
    InventoryService,
    InventoryStoreConflictError,
    SpoolAssignmentConflictError,
)
from foxforge.domain.inventory import SpoolColor
from foxforge.infrastructure.inventory import SQLiteInventoryStore


def test_sqlite_inventory_survives_restart_with_metadata_ledger_and_assignment(tmp_path) -> None:
    database = tmp_path / "inventory.db"
    first = InventoryService(SQLiteInventoryStore(database))
    spool = first.add_spool(
        material_family="PETG",
        initial_filament_mass_g=Decimal("1000"),
        manufacturer="SUNLU",
        product_name="PETG",
        color=SpoolColor("112233FF"),
        empty_spool_mass_g=Decimal("190"),
        purchase_date=date(2026, 9, 1),
    )
    first.consume(
        spool.spool_id,
        Decimal("14.5"),
        idempotency_key="queue:completed:1",
        note="completed print",
    )
    first.correct_by_delta(
        spool.spool_id,
        Decimal("0.5"),
        idempotency_key="manual:scale:1",
        note="scale correction",
    )
    assignment = first.assign_spool(spool.spool_id, "x2d-main", "bambu:unit:0:tray:1")
    updated = first.set_empty_spool_mass(spool.spool_id, Decimal("184.7"))

    reopened = InventoryService(SQLiteInventoryStore(database))

    assert reopened.get_spool(spool.spool_id) == updated
    assert reopened.balance(spool.spool_id).remaining_filament_mass_g == Decimal("986.0")
    assert len(reopened.adjustments(spool.spool_id)) == 2
    assert reopened.assignment_for_spool(spool.spool_id) == assignment
    assert reopened.assignment_for_slot("x2d-main", "bambu:unit:0:tray:1") == assignment


def test_sqlite_adjustment_idempotency_survives_restart_and_archive(tmp_path) -> None:
    database = tmp_path / "inventory.db"
    first = InventoryService(SQLiteInventoryStore(database))
    spool = first.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("1000"))
    adjustment = first.consume(
        spool.spool_id,
        Decimal("20"),
        idempotency_key="queue:completed:42",
        note="completed print",
    )
    first.archive_spool(spool.spool_id)

    reopened = InventoryService(SQLiteInventoryStore(database))
    replay = reopened.consume(
        spool.spool_id,
        Decimal("20"),
        idempotency_key="queue:completed:42",
        note="completed print",
    )

    assert replay == adjustment
    assert reopened.adjustments(spool.spool_id) == (adjustment,)
    assert reopened.balance(spool.spool_id).remaining_filament_mass_g == Decimal("980")

    with pytest.raises(InventoryIdempotencyConflictError, match="different data"):
        reopened.consume(
            spool.spool_id,
            Decimal("21"),
            idempotency_key="queue:completed:42",
            note="completed print",
        )
    with pytest.raises(ArchivedSpoolError, match="adjustments"):
        reopened.consume(spool.spool_id, Decimal("1"), idempotency_key="queue:new")


def test_sqlite_assignment_uniqueness_and_explicit_move_survive_restart(tmp_path) -> None:
    database = tmp_path / "inventory.db"
    inventory = InventoryService(SQLiteInventoryStore(database))
    first = inventory.add_spool(material_family="PETG", initial_filament_mass_g=Decimal("1000"))
    second = inventory.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("1000"))
    slot_id = "bambu:unit:0:tray:2"
    first_assignment = inventory.assign_spool(first.spool_id, "x2d-main", slot_id)

    reopened = InventoryService(SQLiteInventoryStore(database))
    assert reopened.assignment_for_slot("x2d-main", slot_id) == first_assignment

    with pytest.raises(SpoolAssignmentConflictError, match="another spool"):
        reopened.assign_spool(second.spool_id, "x2d-main", slot_id)

    reopened.unassign_spool(first.spool_id)
    second_assignment = reopened.assign_spool(second.spool_id, "x2d-main", slot_id)

    final = InventoryService(SQLiteInventoryStore(database))
    assert final.assignment_for_spool(first.spool_id) is None
    assert final.assignment_for_spool(second.spool_id) == second_assignment
    assert final.assignment_for_slot("x2d-main", slot_id) == second_assignment


def test_sqlite_store_enforces_unique_adjustment_key_below_service_layer(tmp_path) -> None:
    database = tmp_path / "inventory.db"
    store = SQLiteInventoryStore(database)
    inventory = InventoryService(store)
    spool = inventory.add_spool(material_family="TPU", initial_filament_mass_g=Decimal("750"))
    adjustment = inventory.consume(
        spool.spool_id,
        Decimal("5"),
        idempotency_key="queue:completed:99",
    )

    duplicate = replace(adjustment, adjustment_id=uuid4())
    with pytest.raises(InventoryStoreConflictError, match="idempotency key"):
        store.append_adjustment(duplicate)

    assert store.get_adjustment_by_key("queue:completed:99") == adjustment
    assert store.list_adjustments(spool.spool_id) == (adjustment,)
