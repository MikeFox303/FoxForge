# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from foxforge.application.accounting import (
    FilamentAccountingStoreConflictError,
    FilamentAccountingStoreMissingError,
    FilamentReservation,
    FilamentReservationState,
)

_SCHEMA_VERSION = 1


class SQLiteFilamentAccountingStore:
    """Durable reservation state stored in the shared FoxForge SQLite database."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def create(self, reservation: FilamentReservation) -> None:
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    """
                    INSERT INTO filament_reservations(
                        queue_id, material_index, spool_id, state, payload, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(reservation.queue_id),
                        reservation.material_index,
                        str(reservation.spool_id),
                        reservation.state.value,
                        _encode(reservation),
                        reservation.created_at.isoformat(),
                        reservation.updated_at.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise FilamentAccountingStoreConflictError(
                f"reservation already exists: {reservation.queue_id}/{reservation.material_index}"
            ) from error

    def save(self, reservation: FilamentReservation) -> None:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                UPDATE filament_reservations
                SET spool_id = ?, state = ?, payload = ?, updated_at = ?
                WHERE queue_id = ? AND material_index = ?
                """,
                (
                    str(reservation.spool_id),
                    reservation.state.value,
                    _encode(reservation),
                    reservation.updated_at.isoformat(),
                    str(reservation.queue_id),
                    reservation.material_index,
                ),
            )
            if cursor.rowcount != 1:
                raise FilamentAccountingStoreMissingError(
                    f"reservation does not exist: {reservation.queue_id}/{reservation.material_index}"
                )

    def get(self, queue_id: UUID, material_index: int) -> FilamentReservation | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM filament_reservations WHERE queue_id = ? AND material_index = ?",
                (str(queue_id), material_index),
            ).fetchone()
        return None if row is None else _decode(row[0])

    def list_for_queue(self, queue_id: UUID) -> tuple[FilamentReservation, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload FROM filament_reservations
                WHERE queue_id = ? ORDER BY material_index ASC
                """,
                (str(queue_id),),
            ).fetchall()
        return tuple(_decode(row[0]) for row in rows)

    def list_for_spool(self, spool_id: UUID) -> tuple[FilamentReservation, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload FROM filament_reservations
                WHERE spool_id = ? ORDER BY created_at ASC, queue_id ASC, material_index ASC
                """,
                (str(spool_id),),
            ).fetchall()
        return tuple(_decode(row[0]) for row in rows)

    def list(self) -> tuple[FilamentReservation, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload FROM filament_reservations
                ORDER BY created_at ASC, queue_id ASC, material_index ASC
                """
            ).fetchall()
        return tuple(_decode(row[0]) for row in rows)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS filament_reservations (
                    queue_id TEXT NOT NULL,
                    material_index INTEGER NOT NULL,
                    spool_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(queue_id, material_index)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_filament_reservations_spool_state
                ON filament_reservations(spool_id, state, created_at)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA busy_timeout=5000")
        return connection


def _encode(reservation: FilamentReservation) -> str:
    return json.dumps(
        {
            "schema_version": _SCHEMA_VERSION,
            "queue_id": str(reservation.queue_id),
            "material_index": reservation.material_index,
            "spool_id": str(reservation.spool_id),
            "printer_id": reservation.printer_id,
            "slot_id": reservation.slot_id,
            "estimated_mass_g": str(reservation.estimated_mass_g),
            "state": reservation.state.value,
            "created_at": reservation.created_at.isoformat(),
            "updated_at": reservation.updated_at.isoformat(),
            "actual_mass_g": None if reservation.actual_mass_g is None else str(reservation.actual_mass_g),
            "note": reservation.note,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _decode(raw: str) -> FilamentReservation:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("filament reservation payload must be a mapping")
    if payload.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError(f"unsupported filament reservation schema version: {payload.get('schema_version')!r}")
    actual = payload.get("actual_mass_g")
    return FilamentReservation(
        queue_id=UUID(str(payload["queue_id"])),
        material_index=int(payload["material_index"]),
        spool_id=UUID(str(payload["spool_id"])),
        printer_id=str(payload["printer_id"]),
        slot_id=str(payload["slot_id"]),
        estimated_mass_g=Decimal(str(payload["estimated_mass_g"])),
        state=FilamentReservationState(str(payload["state"])),
        created_at=datetime.fromisoformat(str(payload["created_at"])),
        updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        actual_mass_g=None if actual is None else Decimal(str(actual)),
        note=None if payload.get("note") is None else str(payload["note"]),
    )
