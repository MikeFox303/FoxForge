# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from uuid import UUID

from foxforge.application.commands import (
    CommandAuditOutcome,
    CommandAuditRecord,
    CommandExecutionState,
    CommandIdempotencyClaim,
    CommandIdempotencyRecord,
)


class CommandStoreMissingError(KeyError):
    pass


class SQLiteCommandStore:
    """Durable idempotency and audit store for the single-process alpha runtime."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def path(self) -> Path:
        return self._path

    def claim(self, record: CommandIdempotencyRecord) -> CommandIdempotencyClaim:
        if record.state != CommandExecutionState.IN_PROGRESS:
            raise ValueError("new command idempotency claims must start in_progress")
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO command_idempotency(
                    principal_id, operation, key_hash, request_fingerprint,
                    state, created_at, updated_at, result_status, result_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    record.principal_id,
                    record.operation,
                    record.key_hash,
                    record.request_fingerprint,
                    record.state.value,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            row = connection.execute(
                """
                SELECT principal_id, operation, key_hash, request_fingerprint,
                       state, created_at, updated_at, result_status, result_payload_json
                FROM command_idempotency
                WHERE principal_id = ? AND operation = ? AND key_hash = ?
                """,
                (record.principal_id, record.operation, record.key_hash),
            ).fetchone()
        if row is None:
            raise RuntimeError("command idempotency claim was not persisted")
        return CommandIdempotencyClaim(record=_decode_idempotency(row), created=cursor.rowcount == 1)

    def save(self, record: CommandIdempotencyRecord) -> None:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                UPDATE command_idempotency
                SET request_fingerprint = ?, state = ?, updated_at = ?,
                    result_status = ?, result_payload_json = ?
                WHERE principal_id = ? AND operation = ? AND key_hash = ?
                """,
                (
                    record.request_fingerprint,
                    record.state.value,
                    record.updated_at.isoformat(),
                    record.result_status,
                    record.result_payload_json,
                    record.principal_id,
                    record.operation,
                    record.key_hash,
                ),
            )
            if cursor.rowcount != 1:
                raise CommandStoreMissingError((record.principal_id, record.operation, record.key_hash))

    def get(self, principal_id: str, operation: str, key_hash: str) -> CommandIdempotencyRecord | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT principal_id, operation, key_hash, request_fingerprint,
                       state, created_at, updated_at, result_status, result_payload_json
                FROM command_idempotency
                WHERE principal_id = ? AND operation = ? AND key_hash = ?
                """,
                (principal_id, operation, key_hash),
            ).fetchone()
        return None if row is None else _decode_idempotency(row)

    def append_audit(self, record: CommandAuditRecord) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO command_audit(
                    audit_id, request_id, principal_id, action, target_resource,
                    idempotency_key_hash, outcome, error_code, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(record.audit_id),
                    str(record.request_id),
                    record.principal_id,
                    record.action,
                    record.target_resource,
                    record.idempotency_key_hash,
                    record.outcome.value,
                    record.error_code,
                    record.created_at.isoformat(),
                ),
            )

    def list_audit(self) -> tuple[CommandAuditRecord, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT audit_id, request_id, principal_id, action, target_resource,
                       idempotency_key_hash, outcome, error_code, created_at
                FROM command_audit
                ORDER BY created_at ASC, audit_id ASC
                """
            ).fetchall()
        return tuple(_decode_audit(row) for row in rows)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_idempotency (
                    principal_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    request_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    result_status INTEGER,
                    result_payload_json TEXT,
                    PRIMARY KEY(principal_id, operation, key_hash)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_audit (
                    audit_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    principal_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_resource TEXT,
                    idempotency_key_hash TEXT,
                    outcome TEXT NOT NULL,
                    error_code TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS command_audit_created_at_idx ON command_audit(created_at, audit_id)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection


def _decode_idempotency(row: tuple[object, ...]) -> CommandIdempotencyRecord:
    return CommandIdempotencyRecord(
        principal_id=str(row[0]),
        operation=str(row[1]),
        key_hash=str(row[2]),
        request_fingerprint=str(row[3]),
        state=CommandExecutionState(str(row[4])),
        created_at=datetime.fromisoformat(str(row[5])),
        updated_at=datetime.fromisoformat(str(row[6])),
        result_status=None if row[7] is None else int(row[7]),
        result_payload_json=None if row[8] is None else str(row[8]),
    )


def _decode_audit(row: tuple[object, ...]) -> CommandAuditRecord:
    return CommandAuditRecord(
        audit_id=UUID(str(row[0])),
        request_id=UUID(str(row[1])),
        principal_id=str(row[2]),
        action=str(row[3]),
        target_resource=None if row[4] is None else str(row[4]),
        idempotency_key_hash=None if row[5] is None else str(row[5]),
        outcome=CommandAuditOutcome(str(row[6])),
        error_code=None if row[7] is None else str(row[7]),
        created_at=datetime.fromisoformat(str(row[8])),
    )
