# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from foxforge.application.commands import (
    CommandAuditOutcome,
    CommandAuditService,
    CommandExecutionState,
    CommandIdempotencyConflictError,
    CommandIdempotencyService,
    InMemoryCommandStore,
    canonical_json,
    command_request_fingerprint,
    idempotency_key_hash,
    validate_idempotency_key,
)


def test_idempotency_claim_replays_same_request_without_second_execution() -> None:
    store = InMemoryCommandStore()
    service = CommandIdempotencyService(store)
    now = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)
    payload = {"spoolId": "abc", "massG": "14.5"}

    first = service.claim(
        principal_id="operator-a",
        operation="inventory.consume",
        idempotency_key="consume:job-123",
        request_payload=payload,
        now=now,
    )
    replay = service.claim(
        principal_id="operator-a",
        operation="inventory.consume",
        idempotency_key="consume:job-123",
        request_payload={"massG": "14.5", "spoolId": "abc"},
        now=now + timedelta(seconds=1),
    )

    assert first.created is True
    assert replay.created is False
    assert replay.record == first.record
    assert first.record.state == CommandExecutionState.IN_PROGRESS


def test_idempotency_claim_rejects_same_key_with_changed_request() -> None:
    store = InMemoryCommandStore()
    service = CommandIdempotencyService(store)

    service.claim(
        principal_id="operator-a",
        operation="inventory.consume",
        idempotency_key="consume:job-123",
        request_payload={"massG": "14.5"},
    )

    with pytest.raises(CommandIdempotencyConflictError):
        service.claim(
            principal_id="operator-a",
            operation="inventory.consume",
            idempotency_key="consume:job-123",
            request_payload={"massG": "15"},
        )


def test_idempotency_scope_includes_principal_and_operation() -> None:
    store = InMemoryCommandStore()
    service = CommandIdempotencyService(store)

    first = service.claim(
        principal_id="operator-a",
        operation="inventory.consume",
        idempotency_key="shared-key-123",
        request_payload={"massG": "1"},
    )
    other_principal = service.claim(
        principal_id="operator-b",
        operation="inventory.consume",
        idempotency_key="shared-key-123",
        request_payload={"massG": "2"},
    )
    other_operation = service.claim(
        principal_id="operator-a",
        operation="inventory.waste",
        idempotency_key="shared-key-123",
        request_payload={"massG": "3"},
    )

    assert first.created and other_principal.created and other_operation.created


def test_completed_and_indeterminate_results_are_committed_for_replay() -> None:
    store = InMemoryCommandStore()
    service = CommandIdempotencyService(store)
    claim = service.claim(
        principal_id="operator-a",
        operation="queue.dispatch",
        idempotency_key="dispatch:job-123",
        request_payload={"queueId": "q1"},
    )

    completed = service.complete(claim.record, status=202, payload={"state": "accepted"})
    replay = service.get(
        principal_id="operator-a",
        operation="queue.dispatch",
        idempotency_key="dispatch:job-123",
    )

    assert completed.state == CommandExecutionState.COMPLETED
    assert json.loads(completed.result_payload_json or "{}") == {"state": "accepted"}
    assert replay == completed

    second = service.claim(
        principal_id="operator-a",
        operation="queue.reconcile",
        idempotency_key="reconcile:job-123",
        request_payload={"queueId": "q2"},
    )
    uncertain = service.complete(
        second.record,
        status=409,
        payload={"state": "indeterminate", "requiresReconciliation": True},
        indeterminate=True,
    )
    assert uncertain.state == CommandExecutionState.INDETERMINATE


def test_idempotency_key_and_fingerprint_are_stable_and_bounded() -> None:
    assert validate_idempotency_key("alpha_1234") == "alpha_1234"
    assert idempotency_key_hash("alpha_1234") == idempotency_key_hash("alpha_1234")
    assert command_request_fingerprint({"b": 2, "a": 1}) == command_request_fingerprint({"a": 1, "b": 2})
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'

    for invalid in ("short", "contains space", "x" * 129):
        with pytest.raises(ValueError):
            validate_idempotency_key(invalid)


def test_audit_service_hashes_idempotency_key_and_never_stores_raw_value() -> None:
    store = InMemoryCommandStore()
    service = CommandAuditService(store)
    request_id = uuid4()

    record = service.record(
        request_id=request_id,
        principal_id="operator-a",
        action="inventory.consume",
        target_resource="spool:abc",
        idempotency_key="consume:job-123",
        outcome=CommandAuditOutcome.COMPLETED,
    )

    assert record.request_id == request_id
    assert record.idempotency_key_hash == idempotency_key_hash("consume:job-123")
    assert "consume:job-123" not in repr(record)
    assert store.list_audit() == (record,)
