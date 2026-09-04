# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest

from foxforge.application.inventory import InventoryBalanceError, InventoryService
from foxforge.infrastructure.inventory import SQLiteInventoryStore


def _run_pair(first, second):
    barrier = Barrier(2)

    def run(operation):
        barrier.wait(timeout=5)
        try:
            return ("ok", operation())
        except Exception as error:  # noqa: BLE001 - test records the serialized outcome
            return ("error", error)

    with ThreadPoolExecutor(max_workers=2) as executor:
        left = executor.submit(run, first)
        right = executor.submit(run, second)
        return left.result(timeout=10), right.result(timeout=10)


def test_two_simultaneous_deductions_cannot_overdraw_one_spool(tmp_path) -> None:
    database = tmp_path / "inventory.db"
    bootstrap = InventoryService(SQLiteInventoryStore(database))
    spool = bootstrap.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("100"))

    first = InventoryService(SQLiteInventoryStore(database))
    second = InventoryService(SQLiteInventoryStore(database))
    outcomes = _run_pair(
        lambda: first.consume(spool.spool_id, Decimal("60"), idempotency_key="auto:job:1"),
        lambda: second.consume(spool.spool_id, Decimal("60"), idempotency_key="auto:job:2"),
    )

    successes = [value for status, value in outcomes if status == "ok"]
    errors = [value for status, value in outcomes if status == "error"]
    assert len(successes) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], InventoryBalanceError)

    reopened = InventoryService(SQLiteInventoryStore(database))
    assert reopened.balance(spool.spool_id).remaining_filament_mass_g == Decimal("40")
    assert len(reopened.adjustments(spool.spool_id)) == 1


def test_concurrent_duplicate_completion_is_one_ledger_row(tmp_path) -> None:
    database = tmp_path / "inventory.db"
    bootstrap = InventoryService(SQLiteInventoryStore(database))
    spool = bootstrap.add_spool(material_family="PETG", initial_filament_mass_g=Decimal("100"))

    first = InventoryService(SQLiteInventoryStore(database))
    second = InventoryService(SQLiteInventoryStore(database))
    outcomes = _run_pair(
        lambda: first.consume(spool.spool_id, Decimal("20"), idempotency_key="queue:completed:shared"),
        lambda: second.consume(spool.spool_id, Decimal("20"), idempotency_key="queue:completed:shared"),
    )

    assert [status for status, _ in outcomes] == ["ok", "ok"]
    left = outcomes[0][1]
    right = outcomes[1][1]
    assert left == right

    reopened = InventoryService(SQLiteInventoryStore(database))
    assert reopened.balance(spool.spool_id).remaining_filament_mass_g == Decimal("80")
    assert reopened.adjustments(spool.spool_id) == (left,)


def test_manual_correction_racing_consumption_is_serializable(tmp_path) -> None:
    database = tmp_path / "inventory.db"
    bootstrap = InventoryService(SQLiteInventoryStore(database))
    spool = bootstrap.add_spool(material_family="PLA", initial_filament_mass_g=Decimal("100"))
    bootstrap.consume(spool.spool_id, Decimal("40"), idempotency_key="seed")

    correction_service = InventoryService(SQLiteInventoryStore(database))
    consumption_service = InventoryService(SQLiteInventoryStore(database))
    outcomes = _run_pair(
        lambda: correction_service.correct_by_delta(
            spool.spool_id,
            Decimal("40"),
            idempotency_key="manual:correction",
        ),
        lambda: consumption_service.consume(
            spool.spool_id,
            Decimal("80"),
            idempotency_key="auto:completion",
        ),
    )

    reopened = InventoryService(SQLiteInventoryStore(database))
    remaining = reopened.balance(spool.spool_id).remaining_filament_mass_g
    statuses = [status for status, _ in outcomes]

    # The only valid serialized histories are:
    # correction (+40) then consume (-80) => 20, both commit;
    # consume first is rejected at remaining=60, correction commits => 100.
    assert remaining in {Decimal("20"), Decimal("100")}
    if remaining == Decimal("20"):
        assert statuses.count("ok") == 2
        assert len(reopened.adjustments(spool.spool_id)) == 3
    else:
        assert statuses.count("ok") == 1
        errors = [value for status, value in outcomes if status == "error"]
        assert len(errors) == 1
        assert isinstance(errors[0], InventoryBalanceError)
        assert len(reopened.adjustments(spool.spool_id)) == 2


def test_insufficient_balance_rejection_survives_restart_and_replay(tmp_path) -> None:
    database = tmp_path / "inventory.db"
    first = InventoryService(SQLiteInventoryStore(database))
    spool = first.add_spool(material_family="TPU", initial_filament_mass_g=Decimal("50"))
    original = first.consume(spool.spool_id, Decimal("30"), idempotency_key="queue:completed:1")

    reopened = InventoryService(SQLiteInventoryStore(database))
    replay = reopened.consume(spool.spool_id, Decimal("30"), idempotency_key="queue:completed:1")
    assert replay == original

    with pytest.raises(InventoryBalanceError):
        reopened.consume(spool.spool_id, Decimal("21"), idempotency_key="queue:completed:2")

    final = InventoryService(SQLiteInventoryStore(database))
    assert final.balance(spool.spool_id).remaining_filament_mass_g == Decimal("20")
    assert final.adjustments(spool.spool_id) == (original,)
