# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from foxforge.application.commands import (
    CommandIdempotencyConflictError,
    CommandIdempotencyRecord,
    CommandIdempotencyState,
    command_request_fingerprint,
)
from foxforge.infrastructure.commands import SQLiteCommandIdempotencyStore


def _record() -> CommandIdempotencyRecord:
    now = datetime(2026, 9, 4, 10, 30, tzinfo=UTC)
    return CommandIdempotencyRecord(
        principal_id="operator",
        operation="queue.enqueue",
        idempotency_key="queue-command-001",
        request_fingerprint=command_request_fingerprint({"printerId": "printer-a", "artifactId": "artifact-a"}),
        state=CommandIdempotencyState.STARTED,
        created_at=now,
        updated_at=now,
    )


def test_sqlite_command_reservation_and_completion_survive_restart(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    original_store = SQLiteCommandIdempotencyStore(database)
    original = _record()

    first = original_store.reserve(original)
    assert first.created is True
    assert first.record == original

    restarted_store = SQLiteCommandIdempotencyStore(database)
    restored = restarted_store.get(original.principal_id, original.operation, original.idempotency_key)
    assert restored == original
    replay = restarted_store.reserve(original)
    assert replay.created is False
    assert replay.record == original

    completed = restarted_store.complete(
        principal_id=original.principal_id,
        operation=original.operation,
        idempotency_key=original.idempotency_key,
        request_fingerprint=original.request_fingerprint,
        outcome_code="accepted",
        result_ref="2edc0a37-4c17-4239-9c09-bfd1c67ec668",
        completed_at=original.created_at + timedelta(seconds=3),
    )

    final_store = SQLiteCommandIdempotencyStore(database)
    assert final_store.get(original.principal_id, original.operation, original.idempotency_key) == completed
    final_replay = final_store.reserve(original)
    assert final_replay.created is False
    assert final_replay.record == completed


def test_sqlite_started_replay_cannot_be_mistaken_for_new_execution_owner(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    original = _record()

    first = SQLiteCommandIdempotencyStore(database).reserve(original)
    after_restart = SQLiteCommandIdempotencyStore(database).reserve(original)

    assert first.created is True
    assert after_restart.created is False
    assert after_restart.record.state == CommandIdempotencyState.STARTED


def test_sqlite_command_idempotency_rejects_changed_replay_after_restart(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    store = SQLiteCommandIdempotencyStore(database)
    original = _record()
    store.reserve(original)

    restarted_store = SQLiteCommandIdempotencyStore(database)
    changed = CommandIdempotencyRecord(
        principal_id=original.principal_id,
        operation=original.operation,
        idempotency_key=original.idempotency_key,
        request_fingerprint=command_request_fingerprint({"printerId": "printer-b", "artifactId": "artifact-a"}),
        state=CommandIdempotencyState.STARTED,
        created_at=original.created_at,
        updated_at=original.updated_at,
    )

    with pytest.raises(CommandIdempotencyConflictError):
        restarted_store.reserve(changed)
