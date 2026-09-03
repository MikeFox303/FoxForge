# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from foxforge.application.inventory import InventoryStoreConflictError, InventoryStoreMissingError
from foxforge.domain.inventory import (
    Spool,
    SpoolAdjustment,
    SpoolAdjustmentKind,
    SpoolAssignment,
    SpoolColor,
)

_SCHEMA_VERSION = 1


class SQLiteInventoryStore:
    """Durable inventory store for the current single-container FoxForge runtime."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def path(self) -> Path:
        return self._path

    def create_spool(self, spool: Spool) -> None:
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    """
                    INSERT INTO inventory_spools(spool_id, payload, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        str(spool.spool_id),
                        _encode_spool(spool),
                        spool.created_at.isoformat(),
                        spool.updated_at.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise InventoryStoreConflictError(f"spool already exists: {spool.spool_id}") from error

    def save_spool(self, spool: Spool) -> None:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                UPDATE inventory_spools
                SET payload = ?, updated_at = ?
                WHERE spool_id = ?
                """,
                (_encode_spool(spool), spool.updated_at.isoformat(), str(spool.spool_id)),
            )
            if cursor.rowcount != 1:
                raise InventoryStoreMissingError(f"spool does not exist: {spool.spool_id}")

    def get_spool(self, spool_id: UUID) -> Spool | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM inventory_spools WHERE spool_id = ?",
                (str(spool_id),),
            ).fetchone()
        return None if row is None else _decode_spool(row[0])

    def list_spools(self) -> tuple[Spool, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT payload FROM inventory_spools ORDER BY created_at ASC, spool_id ASC"
            ).fetchall()
        return tuple(_decode_spool(row[0]) for row in rows)

    def append_adjustment(self, adjustment: SpoolAdjustment) -> None:
        with closing(self._connect()) as connection, connection:
            if not self._spool_exists(connection, adjustment.spool_id):
                raise InventoryStoreMissingError(f"spool does not exist: {adjustment.spool_id}")
            try:
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
            except sqlite3.IntegrityError as error:
                raise InventoryStoreConflictError(
                    f"adjustment or idempotency key already exists: {adjustment.idempotency_key}"
                ) from error

    def get_adjustment_by_key(self, idempotency_key: str) -> SpoolAdjustment | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM inventory_adjustments WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return None if row is None else _decode_adjustment(row[0])

    def list_adjustments(self, spool_id: UUID) -> tuple[SpoolAdjustment, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload
                FROM inventory_adjustments
                WHERE spool_id = ?
                ORDER BY created_at ASC, adjustment_id ASC
                """,
                (str(spool_id),),
            ).fetchall()
        return tuple(_decode_adjustment(row[0]) for row in rows)

    def save_assignment(self, assignment: SpoolAssignment) -> None:
        with closing(self._connect()) as connection, connection:
            if not self._spool_exists(connection, assignment.spool_id):
                raise InventoryStoreMissingError(f"spool does not exist: {assignment.spool_id}")

            occupied = connection.execute(
                """
                SELECT spool_id
                FROM inventory_assignments
                WHERE printer_id = ? AND slot_id = ? AND spool_id <> ?
                """,
                (assignment.printer_id, assignment.slot_id, str(assignment.spool_id)),
            ).fetchone()
            if occupied is not None:
                raise InventoryStoreConflictError(
                    f"material slot already assigned: {assignment.printer_id}/{assignment.slot_id}"
                )

            try:
                connection.execute(
                    """
                    INSERT INTO inventory_assignments(
                        spool_id,
                        printer_id,
                        slot_id,
                        payload,
                        assigned_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(spool_id) DO UPDATE SET
                        printer_id = excluded.printer_id,
                        slot_id = excluded.slot_id,
                        payload = excluded.payload,
                        assigned_at = excluded.assigned_at
                    """,
                    (
                        str(assignment.spool_id),
                        assignment.printer_id,
                        assignment.slot_id,
                        _encode_assignment(assignment),
                        assignment.assigned_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise InventoryStoreConflictError(
                    f"material slot already assigned: {assignment.printer_id}/{assignment.slot_id}"
                ) from error

    def delete_assignment(self, spool_id: UUID) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "DELETE FROM inventory_assignments WHERE spool_id = ?",
                (str(spool_id),),
            )

    def assignment_for_spool(self, spool_id: UUID) -> SpoolAssignment | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM inventory_assignments WHERE spool_id = ?",
                (str(spool_id),),
            ).fetchone()
        return None if row is None else _decode_assignment(row[0])

    def assignment_for_slot(self, printer_id: str, slot_id: str) -> SpoolAssignment | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload
                FROM inventory_assignments
                WHERE printer_id = ? AND slot_id = ?
                """,
                (printer_id, slot_id),
            ).fetchone()
        return None if row is None else _decode_assignment(row[0])

    def list_assignments(self) -> tuple[SpoolAssignment, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload
                FROM inventory_assignments
                ORDER BY printer_id ASC, slot_id ASC, spool_id ASC
                """
            ).fetchall()
        return tuple(_decode_assignment(row[0]) for row in rows)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_spools (
                    spool_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_adjustments (
                    adjustment_id TEXT PRIMARY KEY,
                    spool_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(spool_id)
                        REFERENCES inventory_spools(spool_id)
                        ON DELETE RESTRICT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_assignments (
                    spool_id TEXT PRIMARY KEY,
                    printer_id TEXT NOT NULL,
                    slot_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    UNIQUE(printer_id, slot_id),
                    FOREIGN KEY(spool_id)
                        REFERENCES inventory_spools(spool_id)
                        ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_inventory_adjustments_spool_created
                ON inventory_adjustments(spool_id, created_at, adjustment_id)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @staticmethod
    def _spool_exists(connection: sqlite3.Connection, spool_id: UUID) -> bool:
        row = connection.execute(
            "SELECT 1 FROM inventory_spools WHERE spool_id = ?",
            (str(spool_id),),
        ).fetchone()
        return row is not None


def _encode_spool(spool: Spool) -> str:
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "spool_id": str(spool.spool_id),
        "material_family": spool.material_family,
        "initial_filament_mass_g": str(spool.initial_filament_mass_g),
        "manufacturer": spool.manufacturer,
        "product_name": spool.product_name,
        "color": spool.color.rgba_hex if spool.color is not None else None,
        "empty_spool_mass_g": (str(spool.empty_spool_mass_g) if spool.empty_spool_mass_g is not None else None),
        "purchase_date": spool.purchase_date.isoformat() if spool.purchase_date is not None else None,
        "created_at": spool.created_at.isoformat(),
        "updated_at": spool.updated_at.isoformat(),
        "archived": spool.archived,
    }
    return _dump(payload)


def _decode_spool(raw: str) -> Spool:
    payload = _load(raw, object_name="spool")
    return Spool(
        spool_id=UUID(str(payload["spool_id"])),
        material_family=str(payload["material_family"]),
        initial_filament_mass_g=Decimal(str(payload["initial_filament_mass_g"])),
        manufacturer=_optional_string(payload.get("manufacturer")),
        product_name=_optional_string(payload.get("product_name")),
        color=(None if payload.get("color") is None else SpoolColor(str(payload["color"]))),
        empty_spool_mass_g=(
            None if payload.get("empty_spool_mass_g") is None else Decimal(str(payload["empty_spool_mass_g"]))
        ),
        purchase_date=(
            None if payload.get("purchase_date") is None else date.fromisoformat(str(payload["purchase_date"]))
        ),
        created_at=datetime.fromisoformat(str(payload["created_at"])),
        updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        archived=bool(payload["archived"]),
    )


def _encode_adjustment(adjustment: SpoolAdjustment) -> str:
    return _dump(
        {
            "schema_version": _SCHEMA_VERSION,
            "adjustment_id": str(adjustment.adjustment_id),
            "spool_id": str(adjustment.spool_id),
            "kind": adjustment.kind.value,
            "delta_filament_mass_g": str(adjustment.delta_filament_mass_g),
            "idempotency_key": adjustment.idempotency_key,
            "created_at": adjustment.created_at.isoformat(),
            "note": adjustment.note,
        }
    )


def _decode_adjustment(raw: str) -> SpoolAdjustment:
    payload = _load(raw, object_name="adjustment")
    return SpoolAdjustment(
        adjustment_id=UUID(str(payload["adjustment_id"])),
        spool_id=UUID(str(payload["spool_id"])),
        kind=SpoolAdjustmentKind(str(payload["kind"])),
        delta_filament_mass_g=Decimal(str(payload["delta_filament_mass_g"])),
        idempotency_key=str(payload["idempotency_key"]),
        created_at=datetime.fromisoformat(str(payload["created_at"])),
        note=_optional_string(payload.get("note")),
    )


def _encode_assignment(assignment: SpoolAssignment) -> str:
    return _dump(
        {
            "schema_version": _SCHEMA_VERSION,
            "spool_id": str(assignment.spool_id),
            "printer_id": assignment.printer_id,
            "slot_id": assignment.slot_id,
            "assigned_at": assignment.assigned_at.isoformat(),
        }
    )


def _decode_assignment(raw: str) -> SpoolAssignment:
    payload = _load(raw, object_name="assignment")
    return SpoolAssignment(
        spool_id=UUID(str(payload["spool_id"])),
        printer_id=str(payload["printer_id"]),
        slot_id=str(payload["slot_id"]),
        assigned_at=datetime.fromisoformat(str(payload["assigned_at"])),
    )


def _dump(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _load(raw: str, *, object_name: str) -> dict[str, object]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"inventory {object_name} payload must be a mapping")
    if payload.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError(f"unsupported inventory {object_name} schema version: {payload.get('schema_version')!r}")
    return payload


def _optional_string(value: object) -> str | None:
    return None if value is None else str(value)
