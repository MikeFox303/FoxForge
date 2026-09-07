# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from foxforge.application.accounting import (
    FilamentAccountingStoreConflictError,
    FilamentAccountingStoreMissingError,
    FilamentReservation,
    FilamentReservationState,
)
from foxforge.infrastructure.accounting import SQLiteFilamentAccountingStore


def _reservation() -> FilamentReservation:
    now = datetime.now(UTC)
    return FilamentReservation(
        queue_id=uuid4(),
        material_index=0,
        spool_id=uuid4(),
        printer_id="printer-1",
        slot_id="opaque-slot-1",
        estimated_mass_g=Decimal("25.125"),
        state=FilamentReservationState.RESERVED,
        created_at=now,
        updated_at=now,
    )


def test_sqlite_reservation_survives_store_restart(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    reservation = _reservation()
    SQLiteFilamentAccountingStore(database).create(reservation)

    restored = SQLiteFilamentAccountingStore(database).get(
        reservation.queue_id,
        reservation.material_index,
    )

    assert restored == reservation
    assert restored is not None
    assert isinstance(restored.estimated_mass_g, Decimal)
    assert restored.estimated_mass_g == Decimal("25.125")


def test_sqlite_store_persists_reconciliation_required_capacity_hold(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    store = SQLiteFilamentAccountingStore(database)
    reservation = _reservation()
    store.create(reservation)
    pending = replace(
        reservation,
        state=FilamentReservationState.RECONCILIATION_REQUIRED,
        updated_at=reservation.updated_at + timedelta(seconds=1),
        note="started print ended without authoritative actual mass",
    )
    store.save(pending)

    restored = SQLiteFilamentAccountingStore(database).get(
        reservation.queue_id,
        reservation.material_index,
    )
    assert restored == pending
    assert restored is not None and restored.holds_capacity is True


def test_sqlite_store_rejects_duplicate_and_missing_rows(tmp_path) -> None:
    store = SQLiteFilamentAccountingStore(tmp_path / "foxforge.sqlite3")
    reservation = _reservation()
    store.create(reservation)

    with pytest.raises(FilamentAccountingStoreConflictError):
        store.create(reservation)

    missing = replace(
        reservation,
        queue_id=uuid4(),
        updated_at=reservation.updated_at + timedelta(seconds=1),
    )
    with pytest.raises(FilamentAccountingStoreMissingError):
        store.save(missing)
