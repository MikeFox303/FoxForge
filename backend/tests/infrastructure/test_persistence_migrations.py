# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from foxforge.infrastructure.persistence import (
    SQLITE_SCHEMA_VERSION,
    SQLiteMigrationError,
    ensure_sqlite_schema,
    sqlite_schema_version,
)

_FIXTURES = Path(__file__).parents[1] / "fixtures" / "persistence"


def _user_version(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])


def test_new_database_is_initialized_with_owned_schema_version(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"

    result = ensure_sqlite_schema(database)

    assert result.previous_version == 0
    assert result.current_version == SQLITE_SCHEMA_VERSION == 1
    assert result.backup_path is None
    assert sqlite_schema_version(database) == 1


def test_legacy_v0_fixture_is_backed_up_and_migrated_without_losing_data(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript((_FIXTURES / "sqlite-v0.sql").read_text(encoding="utf-8"))

    result = ensure_sqlite_schema(database)

    backup = tmp_path / "foxforge.sqlite3.backup-v0"
    assert result.backup_path == backup
    assert backup.is_file()
    assert _user_version(backup) == 0
    assert _user_version(database) == 1

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT queue_id FROM queue_entries").fetchone() == ("legacy-queue",)

    with sqlite3.connect(backup) as connection:
        assert connection.execute("SELECT queue_id FROM queue_entries").fetchone() == ("legacy-queue",)


def test_restarting_after_migration_is_idempotent_and_preserves_backup(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript((_FIXTURES / "sqlite-v0.sql").read_text(encoding="utf-8"))

    first = ensure_sqlite_schema(database)
    assert first.backup_path is not None
    backup_bytes = first.backup_path.read_bytes()

    second = ensure_sqlite_schema(database)

    assert second.previous_version == second.current_version == 1
    assert second.backup_path is None
    assert first.backup_path.read_bytes() == backup_bytes


def test_future_sqlite_schema_version_fails_closed(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version=99")

    with pytest.raises(SQLiteMigrationError, match="newer than supported"):
        ensure_sqlite_schema(database)

    assert _user_version(database) == 99


def test_incompatible_legacy_table_rolls_back_version_and_keeps_backup(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE inventory_spools(spool_id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO inventory_spools(spool_id) VALUES ('legacy-spool')")

    with pytest.raises(SQLiteMigrationError, match="incompatible"):
        ensure_sqlite_schema(database)

    assert _user_version(database) == 0
    assert (tmp_path / "foxforge.sqlite3.backup-v0").is_file()
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT spool_id FROM inventory_spools").fetchone() == ("legacy-spool",)


def test_corrupt_sqlite_file_fails_without_silent_replacement(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    original = b"not-a-sqlite-database"
    database.write_bytes(original)

    with pytest.raises(SQLiteMigrationError, match="unable to migrate"):
        ensure_sqlite_schema(database)

    assert database.read_bytes() == original
