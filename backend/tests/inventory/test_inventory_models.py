# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from foxforge.domain.inventory import (
    Spool,
    SpoolAdjustment,
    SpoolAdjustmentKind,
    SpoolBalance,
    SpoolColor,
)


def test_spool_color_is_normalized_and_validated() -> None:
    assert SpoolColor("aabbccdd").rgba_hex == "AABBCCDD"
    assert SpoolColor("AABBCC").rgba_hex == "AABBCC"

    with pytest.raises(ValueError, match="6 or 8"):
        SpoolColor("ABC")
    with pytest.raises(ValueError, match="hexadecimal"):
        SpoolColor("GGGGGG")


def test_spool_requires_decimal_positive_filament_mass() -> None:
    now = datetime.now(UTC)
    with pytest.raises(TypeError, match="Decimal"):
        Spool(
            spool_id=uuid4(),
            material_family="PLA",
            initial_filament_mass_g=1000,  # type: ignore[arg-type]
            manufacturer=None,
            product_name=None,
            color=None,
            empty_spool_mass_g=None,
            purchase_date=None,
            created_at=now,
            updated_at=now,
        )

    with pytest.raises(ValueError, match="positive"):
        Spool(
            spool_id=uuid4(),
            material_family="PLA",
            initial_filament_mass_g=Decimal("0"),
            manufacturer=None,
            product_name=None,
            color=None,
            empty_spool_mass_g=None,
            purchase_date=None,
            created_at=now,
            updated_at=now,
        )


def test_adjustment_kind_enforces_mass_direction() -> None:
    now = datetime.now(UTC)
    spool_id = uuid4()

    with pytest.raises(ValueError, match="decrease"):
        SpoolAdjustment(
            adjustment_id=uuid4(),
            spool_id=spool_id,
            kind=SpoolAdjustmentKind.CONSUMPTION,
            delta_filament_mass_g=Decimal("1"),
            idempotency_key="consume:1",
            created_at=now,
        )

    with pytest.raises(ValueError, match="increase"):
        SpoolAdjustment(
            adjustment_id=uuid4(),
            spool_id=spool_id,
            kind=SpoolAdjustmentKind.RETURN,
            delta_filament_mass_g=Decimal("-1"),
            idempotency_key="return:1",
            created_at=now,
        )

    correction = SpoolAdjustment(
        adjustment_id=uuid4(),
        spool_id=spool_id,
        kind=SpoolAdjustmentKind.CORRECTION,
        delta_filament_mass_g=Decimal("2.5"),
        idempotency_key="correction:1",
        created_at=now,
    )
    assert correction.delta_filament_mass_g == Decimal("2.5")


def test_spool_balance_requires_consistent_values() -> None:
    spool_id = uuid4()
    balance = SpoolBalance(
        spool_id=spool_id,
        initial_filament_mass_g=Decimal("1000"),
        remaining_filament_mass_g=Decimal("750"),
        used_filament_mass_g=Decimal("250"),
        used_fraction=Decimal("0.25"),
    )
    assert balance.remaining_filament_mass_g == Decimal("750")

    with pytest.raises(ValueError, match="initial minus remaining"):
        SpoolBalance(
            spool_id=spool_id,
            initial_filament_mass_g=Decimal("1000"),
            remaining_filament_mass_g=Decimal("750"),
            used_filament_mass_g=Decimal("200"),
            used_fraction=Decimal("0.25"),
        )
