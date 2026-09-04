# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import sqlite3
from contextlib import closing
from uuid import uuid4

import pytest

from foxforge.application.commands import (
    CommandAuditOutcome,
    CommandAuditService,
    CommandExecutionState,
    CommandIdempotencyConflictError,
    CommandIdempotencyService,
    idempotency_key_hash,
)
from foxforge.infrastructure.commands import SQLiteCommandStore


def test_sqlite_command_idempotency_survives_restart_and_replays_result(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    first_store = SQLiteCommandStore(database)
    first_service = CommandIdempotencyService(first_store)

    claim = first_service.claim(
        principal_id="operator-a",
        operation="inventory.consume",
        idempotency_key="consume:restart-123",
        request_payload={"spoolId": "spool-a", "massG": "7.25"},
    )
    assert claim.created is True
    completed = first_service.complete(
        claim.record,
        status=200,
        payload={"remainingFilamentMassG": "992.75"},
    )

    second_store = SQLiteCommandStore(database)
    second_service = CommandIdempotencyService(second_store)
    replay = second_service.claim(
        principal_id="operator-a",
        operation="inventory.consume",
        idempotency_key="consume:restart-123",
        request_payload={"massG": "7.25", "spoolId": "spool-a"},
    )

    assert replay.created is False
    assert replay.record == completed
    assert replay.record.state == CommandExecutionState.COMPLETED


def test_sqlite_command_claim_conflict_survives_new_store_instance(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    CommandIdempotencyService(SQLiteCommandStore(database)).claim(
        principal_id="operator-a",
        operation="inventory.consume",
        idempotency_key="consume:conflict-123",
        request_payload={"massG": "1"},
    )

    with pytest.raises(CommandIdempotencyConflictError):
        CommandIdempotencyService(SQLiteCommandStore(database)).claim(
            principal_id="operator-a",
            operation="inventory.consume",
            idempotency_key="consume:conflict-123",
            request_payload={"massG": "2"},
        )


def test_sqlite_command_store_preserves_in_progress_claim_across_restart(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    first = CommandIdempotencyService(SQLiteCommandStore(database)).claim(
        principal_id="operator-a",
        operation="queue.dispatch",
        idempotency_key="dispatch:pending-123",
        request_payload={"queueId": "q-1"},
    )

    replay = CommandIdempotencyService(SQLiteCommandStore(database)).claim(
        principal_id="operator-a",
        operation="queue.dispatch",
        idempotency_key="dispatch:pending-123",
        request_payload={"queueId": "q-1"},
    )

    assert first.created is True
    assert replay.created is False
    assert replay.record.state == CommandExecutionState.IN_PROGRESS


def test_sqlite_command_audit_is_durable_and_raw_idempotency_key_is_not_stored(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    raw_key = "inventory:secret-ish-123"
    first_store = SQLiteCommandStore(database)
    audit = CommandAuditService(first_store).record(
        request_id=uuid4(),
        principal_id="operator-a",
        action="inventory.consume",
        target_resource="spool:abc",
        idempotency_key=raw_key,
        outcome=CommandAuditOutcome.COMPLETED,
    )

    records = SQLiteCommandStore(database).list_audit()

    assert records == (audit,)
    assert records[0].idempotency_key_hash == idempotency_key_hash(raw_key)
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT idempotency_key_hash FROM command_audit WHERE audit_id = ?",
            (str(audit.audit_id),),
        ).fetchone()
    assert row == (idempotency_key_hash(raw_key),)
    assert raw_key not in database.read_bytes().decode("utf-8", errors="ignore")
