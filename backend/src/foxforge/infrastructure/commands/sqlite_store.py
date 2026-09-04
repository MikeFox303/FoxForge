# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from foxforge.application.commands import (
    CommandIdempotencyConflictError,
    CommandIdempotencyMissingError,
    CommandIdempotencyRecord,
    CommandIdempotencyReservation,
    CommandIdempotencyState,
)


class SQLiteCommandIdempotencyStore:
    """Durable command replay reservations for the single-container runtime."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def path(self) -> Path:
        return self._path

    def reserve(self, record: CommandIdempotencyRecord) -> CommandIdempotencyReservation:
        if record.state != CommandIdempotencyState.STARTED:
            raise ValueError("new command idempotency reservations must start in STARTED state")

        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._select(
                connection,
                record.principal_id,
                record.operation,
                record.idempotency_key,
            )
            if existing is not None:
                _require_same_fingerprint(existing, record.request_fingerprint)
                return CommandIdempotencyReservation(record=existing, created=False)

            connection.execute(
                """
                INSERT INTO command_idempotency(
                    principal_id,
                    operation,
                    idempotency_key,
                    request_fingerprint,
                    state,
                    result_ref,
                    outcome_code,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                """,
                (
                    record.principal_id,
                    record.operation,
                    record.idempotency_key,
                    record.request_fingerprint,
                    record.state.value,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            return CommandIdempotencyReservation(record=record, created=True)

    def complete(
        self,
        *,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        request_fingerprint: str,
        outcome_code: str,
        result_ref: str | None = None,
        completed_at: datetime | None = None,
    ) -> CommandIdempotencyRecord:
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._select(connection, principal_id, operation, idempotency_key)
            if existing is None:
                raise CommandIdempotencyMissingError((principal_id, operation, idempotency_key))
            _require_same_fingerprint(existing, request_fingerprint)

            if existing.state == CommandIdempotencyState.COMPLETED:
                if existing.outcome_code == outcome_code and existing.result_ref == result_ref:
                    return existing
                raise CommandIdempotencyConflictError("completed idempotency record has a different terminal result")

            updated_at = (completed_at or datetime.now(UTC)).astimezone(UTC)
            connection.execute(
                """
                UPDATE command_idempotency
                SET state = ?, result_ref = ?, outcome_code = ?, updated_at = ?
                WHERE principal_id = ? AND operation = ? AND idempotency_key = ?
                """,
                (
                    CommandIdempotencyState.COMPLETED.value,
                    result_ref,
                    outcome_code,
                    updated_at.isoformat(),
                    principal_id,
                    operation,
                    idempotency_key,
                ),
            )
            return CommandIdempotencyRecord(
                principal_id=existing.principal_id,
                operation=existing.operation,
                idempotency_key=existing.idempotency_key,
                request_fingerprint=existing.request_fingerprint,
                state=CommandIdempotencyState.COMPLETED,
                result_ref=result_ref,
                outcome_code=outcome_code,
                created_at=existing.created_at,
                updated_at=updated_at,
            )

    def get(
        self,
        principal_id: str,
        operation: str,
        idempotency_key: str,
    ) -> CommandIdempotencyRecord | None:
        with closing(self._connect()) as connection:
            return self._select(connection, principal_id, operation, idempotency_key)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_idempotency (
                    principal_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_ref TEXT,
                    outcome_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (principal_id, operation, idempotency_key)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @staticmethod
    def _select(
        connection: sqlite3.Connection,
        principal_id: str,
        operation: str,
        idempotency_key: str,
    ) -> CommandIdempotencyRecord | None:
        row = connection.execute(
            """
            SELECT request_fingerprint, state, result_ref, outcome_code, created_at, updated_at
            FROM command_idempotency
            WHERE principal_id = ? AND operation = ? AND idempotency_key = ?
            """,
            (principal_id, operation, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        return CommandIdempotencyRecord(
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            request_fingerprint=str(row[0]),
            state=CommandIdempotencyState(str(row[1])),
            result_ref=None if row[2] is None else str(row[2]),
            outcome_code=None if row[3] is None else str(row[3]),
            created_at=_parse_datetime(str(row[4])),
            updated_at=_parse_datetime(str(row[5])),
        )


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("stored command idempotency timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _require_same_fingerprint(record: CommandIdempotencyRecord, request_fingerprint: str) -> None:
    if record.request_fingerprint != request_fingerprint:
        raise CommandIdempotencyConflictError("idempotency key was already used with a different request")
