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
    InMemoryFilamentAccountingStore,
    MaterialEstimate,
)


def _reservation(*, material_index: int = 0) -> FilamentReservation:
    now = datetime.now(UTC)
    return FilamentReservation(
        queue_id=uuid4(),
        material_index=material_index,
        spool_id=uuid4(),
        printer_id="printer-1",
        slot_id="opaque-slot-1",
        estimated_mass_g=Decimal("12.50"),
        state=FilamentReservationState.RESERVED,
        created_at=now,
        updated_at=now,
    )


def test_material_estimate_requires_exact_positive_decimal() -> None:
    assert MaterialEstimate(0, Decimal("12.50")).estimated_mass_g == Decimal("12.50")
    with pytest.raises(TypeError):
        MaterialEstimate(0, 12.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        MaterialEstimate(0, Decimal("0"))


def test_indeterminate_reconciliation_state_keeps_reserved_capacity() -> None:
    reserved = _reservation()
    pending = replace(reserved, state=FilamentReservationState.RECONCILIATION_REQUIRED)
    released = replace(
        reserved,
        state=FilamentReservationState.RELEASED,
        actual_mass_g=Decimal("0"),
    )

    assert reserved.holds_capacity is True
    assert pending.holds_capacity is True
    assert released.holds_capacity is False


def test_consumed_and_released_states_validate_actual_mass() -> None:
    reserved = _reservation()
    with pytest.raises(ValueError):
        replace(reserved, state=FilamentReservationState.CONSUMED)
    with pytest.raises(ValueError):
        replace(
            reserved,
            state=FilamentReservationState.RELEASED,
            actual_mass_g=Decimal("1"),
        )


def test_in_memory_store_rejects_duplicate_create_and_missing_save() -> None:
    store = InMemoryFilamentAccountingStore()
    reservation = _reservation()
    store.create(reservation)

    with pytest.raises(FilamentAccountingStoreConflictError):
        store.create(reservation)

    missing = replace(reservation, queue_id=uuid4(), updated_at=reservation.updated_at + timedelta(seconds=1))
    with pytest.raises(FilamentAccountingStoreMissingError):
        store.save(missing)


def test_in_memory_store_orders_materials_within_queue() -> None:
    store = InMemoryFilamentAccountingStore()
    queue_id = uuid4()
    now = datetime.now(UTC)
    second = replace(_reservation(material_index=1), queue_id=queue_id, created_at=now, updated_at=now)
    first = replace(_reservation(material_index=0), queue_id=queue_id, created_at=now, updated_at=now)
    store.create(second)
    store.create(first)

    assert [item.material_index for item in store.list_for_queue(queue_id)] == [0, 1]
