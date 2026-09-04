# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from foxforge.application.commands import (
    CommandIdempotencyConflictError,
    CommandIdempotencyRecord,
    CommandIdempotencyState,
    InMemoryCommandIdempotencyStore,
    command_request_fingerprint,
)


def _record(*, fingerprint: str | None = None) -> CommandIdempotencyRecord:
    now = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)
    return CommandIdempotencyRecord(
        principal_id="operator",
        operation="inventory.spool.create",
        idempotency_key="client-command-001",
        request_fingerprint=fingerprint or command_request_fingerprint({"materialFamily": "PETG", "mass": "1000"}),
        state=CommandIdempotencyState.STARTED,
        created_at=now,
        updated_at=now,
    )


def test_same_idempotency_key_and_fingerprint_replays_same_reservation() -> None:
    store = InMemoryCommandIdempotencyStore()
    original = _record()

    assert store.reserve(original) == original
    assert store.reserve(_record()) == original


def test_changed_request_with_same_idempotency_key_conflicts() -> None:
    store = InMemoryCommandIdempotencyStore()
    store.reserve(_record())

    with pytest.raises(CommandIdempotencyConflictError):
        store.reserve(_record(fingerprint=command_request_fingerprint({"materialFamily": "PLA", "mass": "1000"})))


def test_completed_idempotency_record_replays_terminal_result() -> None:
    store = InMemoryCommandIdempotencyStore()
    original = store.reserve(_record())
    completed_at = original.created_at + timedelta(seconds=2)

    completed = store.complete(
        principal_id=original.principal_id,
        operation=original.operation,
        idempotency_key=original.idempotency_key,
        request_fingerprint=original.request_fingerprint,
        outcome_code="created",
        result_ref="c0a8012a-5a04-4d5e-93bc-7131f957ce11",
        completed_at=completed_at,
    )

    assert completed.state == CommandIdempotencyState.COMPLETED
    assert completed.result_ref == "c0a8012a-5a04-4d5e-93bc-7131f957ce11"
    assert completed.outcome_code == "created"
    assert store.reserve(_record()) == completed
    assert (
        store.complete(
            principal_id=original.principal_id,
            operation=original.operation,
            idempotency_key=original.idempotency_key,
            request_fingerprint=original.request_fingerprint,
            outcome_code="created",
            result_ref="c0a8012a-5a04-4d5e-93bc-7131f957ce11",
            completed_at=completed_at + timedelta(seconds=1),
        )
        == completed
    )


def test_command_fingerprint_is_stable_for_json_key_order() -> None:
    assert command_request_fingerprint({"a": 1, "b": {"x": "2"}}) == command_request_fingerprint(
        {"b": {"x": "2"}, "a": 1}
    )
