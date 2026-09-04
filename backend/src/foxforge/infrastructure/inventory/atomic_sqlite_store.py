# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import sqlite3
from contextlib import closing
from decimal import Decimal

from foxforge.application.inventory import (
    AdjustmentWriteResult,
    InventoryStoreArchivedError,
    InventoryStoreBalanceError,
    InventoryStoreConflictError,
    InventoryStoreMissingError,
)
from foxforge.domain.inventory import SpoolAdjustment

from .sqlite_store import (
    SQLiteInventoryStore as _BaseSQLiteInventoryStore,
    _decode_adjustment,
    _decode_spool,
    _encode_adjustment,
)


class SQLiteInventoryStore(_BaseSQLiteInventoryStore):
    """SQLite inventory store with a serialized mass-ledger write boundary.

    ``BEGIN IMMEDIATE`` is the linearization point for each adjustment. The
    idempotency lookup, spool/archive check, exact-Decimal balance calculation
    and INSERT therefore observe one serialized writer order.
    """

    def append_adjustment(self, adjustment: SpoolAdjustment) -> AdjustmentWriteResult:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing_row = connection.execute(
                    "SELECT payload FROM inventory_adjustments WHERE idempotency_key = ?",
                    (adjustment.idempotency_key,),
                ).fetchone()
                if existing_row is not None:
                    existing = _decode_adjustment(existing_row[0])
                    connection.commit()
                    return AdjustmentWriteResult(existing, created=False)

                spool_row = connection.execute(
                    "SELECT payload FROM inventory_spools WHERE spool_id = ?",
                    (str(adjustment.spool_id),),
                ).fetchone()
                if spool_row is None:
                    raise InventoryStoreMissingError(f"spool does not exist: {adjustment.spool_id}")

                spool = _decode_spool(spool_row[0])
                if spool.archived:
                    raise InventoryStoreArchivedError("archived spool cannot receive new mass adjustments")

                adjustment_rows = connection.execute(
                    "SELECT payload FROM inventory_adjustments WHERE spool_id = ?",
                    (str(adjustment.spool_id),),
                ).fetchall()
                current = spool.initial_filament_mass_g + sum(
                    (_decode_adjustment(row[0]).delta_filament_mass_g for row in adjustment_rows),
                    start=Decimal("0"),
                )
                next_remaining = current + adjustment.delta_filament_mass_g
                if next_remaining < 0:
                    raise InventoryStoreBalanceError("adjustment would make remaining filament negative")
                if next_remaining > spool.initial_filament_mass_g:
                    raise InventoryStoreBalanceError("adjustment would exceed initial filament mass")

                connection.execute(
                    """
                    INSERT INTO inventory_adjustments(
                        adjustment_id,
                        spool_id,
                        idempotency_key,
                        payload,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(adjustment.adjustment_id),
                        str(adjustment.spool_id),
                        adjustment.idempotency_key,
                        _encode_adjustment(adjustment),
                        adjustment.created_at.isoformat(),
                    ),
                )
                connection.commit()
                return AdjustmentWriteResult(adjustment, created=True)
            except (InventoryStoreMissingError, InventoryStoreArchivedError, InventoryStoreBalanceError):
                connection.rollback()
                raise
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise InventoryStoreConflictError(
                    f"adjustment or idempotency key already exists: {adjustment.idempotency_key}"
                ) from error
            except Exception:
                connection.rollback()
                raise
