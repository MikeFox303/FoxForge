# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

SQLITE_SCHEMA_VERSION = 1

_EXPECTED_TABLES = frozenset(
    {
        "queue_entries",
        "inventory_spools",
        "inventory_adjustments",
        "inventory_assignments",
        "command_idempotency",
        "command_audit",
    }
)

_SCHEMA_V1_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS queue_entries (
        queue_id TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS inventory_spools (
        spool_id TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
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
    """,
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
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_inventory_adjustments_spool_created
    ON inventory_adjustments(spool_id, created_at, adjustment_id)
    """,
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
    """,
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
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_command_audit_request_id
    ON command_audit(request_id, occurred_at)
    """,
)


class SQLiteMigrationError(RuntimeError):
    """Raised when FoxForge cannot safely establish the owned SQLite schema."""


@dataclass(frozen=True, slots=True)
class SQLiteMigrationResult:
    previous_version: int
    current_version: int
    backup_path: Path | None


def ensure_sqlite_schema(path: Path | str) -> SQLiteMigrationResult:
    """Migrate the shared FoxForge SQLite database to the current schema.

    Alpha databases created before migration ownership have ``user_version=0``.
    Existing v0 databases are backed up with SQLite's backup API before the
    transactional baseline migration is attempted. Future schema versions fail
    closed instead of being opened by older FoxForge code.
    """

    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    existed = database_path.exists() and database_path.stat().st_size > 0

    try:
        with closing(_connect(database_path)) as connection:
            previous_version = _user_version(connection)
            if previous_version > SQLITE_SCHEMA_VERSION:
                raise SQLiteMigrationError(
                    f"FoxForge SQLite schema version {previous_version} is newer than supported version "
                    f"{SQLITE_SCHEMA_VERSION}"
                )
            if previous_version < 0:
                raise SQLiteMigrationError(f"invalid FoxForge SQLite schema version: {previous_version}")
            if previous_version == SQLITE_SCHEMA_VERSION:
                _validate_current_schema(connection)
                return SQLiteMigrationResult(previous_version, SQLITE_SCHEMA_VERSION, None)

            backup_path = _backup_legacy_database(connection, database_path) if existed else None
            _migrate_v0_to_v1(connection)
            return SQLiteMigrationResult(previous_version, SQLITE_SCHEMA_VERSION, backup_path)
    except SQLiteMigrationError:
        raise
    except sqlite3.DatabaseError as error:
        raise SQLiteMigrationError(f"unable to migrate FoxForge SQLite database: {database_path}") from error


def sqlite_schema_version(path: Path | str) -> int:
    database_path = Path(path)
    if not database_path.exists():
        return 0
    try:
        with closing(_connect(database_path)) as connection:
            return _user_version(connection)
    except sqlite3.DatabaseError as error:
        raise SQLiteMigrationError(f"unable to read FoxForge SQLite schema version: {database_path}") from error


def _migrate_v0_to_v1(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        for statement in _SCHEMA_V1_STATEMENTS:
            connection.execute(statement)
        _validate_schema_tables(connection)
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise SQLiteMigrationError("FoxForge SQLite migration failed foreign-key validation")
        connection.execute(f"PRAGMA user_version={SQLITE_SCHEMA_VERSION}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _validate_current_schema(connection: sqlite3.Connection) -> None:
    _validate_schema_tables(connection)
    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise SQLiteMigrationError("FoxForge SQLite schema has foreign-key violations")


def _validate_schema_tables(connection: sqlite3.Connection) -> None:
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if not str(row[0]).startswith("sqlite_")
    }
    missing = sorted(_EXPECTED_TABLES - tables)
    if missing:
        raise SQLiteMigrationError(
            "FoxForge SQLite schema is incomplete for the recorded version; missing tables: " + ", ".join(missing)
        )


def _backup_legacy_database(connection: sqlite3.Connection, database_path: Path) -> Path:
    backup_path = database_path.with_name(f"{database_path.name}.backup-v0")
    if backup_path.exists():
        # A previous interrupted attempt may have already created the recovery
        # point. Never overwrite it silently.
        return backup_path

    with closing(sqlite3.connect(backup_path)) as backup_connection:
        connection.backup(backup_connection)
    return backup_path


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=5.0)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def _user_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    if row is None:
        raise SQLiteMigrationError("unable to read FoxForge SQLite user_version")
    return int(row[0])
