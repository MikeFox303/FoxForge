# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from datetime import UTC, datetime

from foxforge.application.commands import (
    CommandAuditOutcome,
    CommandAuditRecord,
    command_idempotency_key_digest,
)
from foxforge.infrastructure.commands import SQLiteCommandAuditStore


def test_sqlite_command_audit_is_append_only_and_restart_safe(tmp_path) -> None:
    database = tmp_path / "foxforge.sqlite3"
    digest = command_idempotency_key_digest("queue-dispatch-1")
    first = CommandAuditRecord(
        request_id="req-1",
        principal_id="operator",
        action="queue.dispatch",
        target_ref="153b6d90-5bb1-49fd-b90a-4316ba57db88",
        idempotency_key_digest=digest,
        outcome=CommandAuditOutcome.ACCEPTED,
        occurred_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )
    second = CommandAuditRecord(
        request_id="req-1",
        principal_id="operator",
        action="queue.dispatch",
        target_ref="153b6d90-5bb1-49fd-b90a-4316ba57db88",
        idempotency_key_digest=digest,
        outcome=CommandAuditOutcome.COMPLETED,
        occurred_at=datetime(2026, 9, 4, 12, 0, 1, tzinfo=UTC),
    )

    store = SQLiteCommandAuditStore(database)
    store.append(first)
    store.append(second)

    restored = SQLiteCommandAuditStore(database).list_for_request("req-1")
    assert restored == (first, second)
    assert restored[0].audit_id != restored[1].audit_id
    assert restored[0].idempotency_key_digest == digest
    assert restored[0].idempotency_key_digest != "queue-dispatch-1"
