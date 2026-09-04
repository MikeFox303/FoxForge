# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from foxforge.application.commands.audit import CommandAuditOutcome, CommandAuditRecord


class SQLiteCommandAuditStore:
    """Append-only command audit log stored beside other FoxForge runtime state."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: CommandAuditRecord) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO command_audit(
                    audit_id,
                    request_id,
                    principal_id,
                    action,
                    target_ref,
                    idempotency_key_digest,
                    outcome,
                    error_code,
                    occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(record.audit_id),
                    record.request_id,
                    record.principal_id,
                    record.action,
                    record.target_ref,
                    record.idempotency_key_digest,
                    record.outcome.value,
                    record.error_code,
                    record.occurred_at.isoformat(),
                ),
            )

    def list_for_request(self, request_id: str) -> tuple[CommandAuditRecord, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT audit_id, principal_id, action, target_ref, idempotency_key_digest,
                       outcome, error_code, occurred_at
                FROM command_audit
                WHERE request_id = ?
                ORDER BY occurred_at, audit_id
                """,
                (request_id,),
            ).fetchall()
        return tuple(
            CommandAuditRecord(
                audit_id=UUID(str(row[0])),
                request_id=request_id,
                principal_id=None if row[1] is None else str(row[1]),
                action=str(row[2]),
                target_ref=None if row[3] is None else str(row[3]),
                idempotency_key_digest=None if row[4] is None else str(row[4]),
                outcome=CommandAuditOutcome(str(row[5])),
                error_code=None if row[6] is None else str(row[6]),
                occurred_at=_parse_datetime(str(row[7])),
            )
            for row in rows
        )

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_audit (
                    audit_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    principal_id TEXT,
                    action TEXT NOT NULL,
                    target_ref TEXT,
                    idempotency_key_digest TEXT,
                    outcome TEXT NOT NULL,
                    error_code TEXT,
                    occurred_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_command_audit_request_id ON command_audit(request_id, occurred_at)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA foreign_keys=ON")
        return connection


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("stored command audit timestamp must be timezone-aware")
    return parsed.astimezone(UTC)
