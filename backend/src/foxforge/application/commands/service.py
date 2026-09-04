# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from .models import (
    CommandAuditOutcome,
    CommandAuditRecord,
    CommandExecutionState,
    CommandIdempotencyClaim,
    CommandIdempotencyRecord,
)
from .store import CommandAuditStore, CommandIdempotencyStore

_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9._~:-]{8,128}$")


class CommandIdempotencyConflictError(RuntimeError):
    def __init__(self, existing: CommandIdempotencyRecord) -> None:
        self.existing = existing
        super().__init__("idempotency key already exists with a different request fingerprint")


class CommandIdempotencyService:
    """Durably claim and complete externally supplied command identities."""

    def __init__(self, store: CommandIdempotencyStore) -> None:
        self._store = store

    def claim(
        self,
        *,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        request_payload: object,
        now: datetime | None = None,
    ) -> CommandIdempotencyClaim:
        key = validate_idempotency_key(idempotency_key)
        principal = _required_text(principal_id, field_name="principal_id")
        command = _required_text(operation, field_name="operation")
        instant = _utc_now(now)
        proposed = CommandIdempotencyRecord(
            principal_id=principal,
            operation=command,
            key_hash=idempotency_key_hash(key),
            request_fingerprint=command_request_fingerprint(request_payload),
            state=CommandExecutionState.IN_PROGRESS,
            created_at=instant,
            updated_at=instant,
        )
        claim = self._store.claim(proposed)
        if claim.record.request_fingerprint != proposed.request_fingerprint:
            raise CommandIdempotencyConflictError(claim.record)
        return claim

    def complete(
        self,
        record: CommandIdempotencyRecord,
        *,
        status: int,
        payload: object,
        indeterminate: bool = False,
        now: datetime | None = None,
    ) -> CommandIdempotencyRecord:
        if record.state != CommandExecutionState.IN_PROGRESS:
            return record
        payload_json = canonical_json(payload)
        updated = replace(
            record,
            state=CommandExecutionState.INDETERMINATE if indeterminate else CommandExecutionState.COMPLETED,
            updated_at=_utc_now(now),
            result_status=status,
            result_payload_json=payload_json,
        )
        self._store.save(updated)
        return updated

    def get(self, *, principal_id: str, operation: str, idempotency_key: str) -> CommandIdempotencyRecord | None:
        return self._store.get(
            _required_text(principal_id, field_name="principal_id"),
            _required_text(operation, field_name="operation"),
            idempotency_key_hash(validate_idempotency_key(idempotency_key)),
        )


class CommandAuditService:
    def __init__(self, store: CommandAuditStore) -> None:
        self._store = store

    def record(
        self,
        *,
        request_id: UUID,
        principal_id: str,
        action: str,
        outcome: CommandAuditOutcome,
        target_resource: str | None = None,
        idempotency_key: str | None = None,
        error_code: str | None = None,
        created_at: datetime | None = None,
    ) -> CommandAuditRecord:
        record = CommandAuditRecord(
            audit_id=uuid4(),
            request_id=request_id,
            principal_id=_required_text(principal_id, field_name="principal_id"),
            action=_required_text(action, field_name="action"),
            outcome=outcome,
            created_at=_utc_now(created_at),
            target_resource=(None if target_resource is None else _required_text(target_resource, field_name="target_resource")),
            idempotency_key_hash=(
                None
                if idempotency_key is None
                else idempotency_key_hash(validate_idempotency_key(idempotency_key))
            ),
            error_code=(None if error_code is None else _required_text(error_code, field_name="error_code")),
        )
        self._store.append_audit(record)
        return record


def validate_idempotency_key(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("idempotency_key must be a string")
    key = value.strip()
    if not _IDEMPOTENCY_KEY.fullmatch(key):
        raise ValueError("idempotency_key must be 8-128 characters from A-Z, a-z, 0-9, . _ ~ : -")
    return key


def idempotency_key_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def command_request_fingerprint(payload: object) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def canonical_json(payload: object) -> str:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError("command payload must be canonical JSON-compatible data") from error


def _required_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _utc_now(value: datetime | None) -> datetime:
    instant = value or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("command timestamp must be timezone-aware")
    return instant.astimezone(UTC)
