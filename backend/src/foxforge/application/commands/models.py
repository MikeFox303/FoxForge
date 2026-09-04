# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class CommandExecutionState(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    INDETERMINATE = "indeterminate"


class CommandAuditOutcome(StrEnum):
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CONFLICT = "conflict"
    DENIED = "denied"
    INDETERMINATE = "indeterminate"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CommandIdempotencyRecord:
    principal_id: str
    operation: str
    key_hash: str
    request_fingerprint: str
    state: CommandExecutionState
    created_at: datetime
    updated_at: datetime
    result_status: int | None = None
    result_payload_json: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.principal_id, field_name="principal_id")
        _require_text(self.operation, field_name="operation")
        _require_sha256(self.key_hash, field_name="key_hash")
        _require_sha256(self.request_fingerprint, field_name="request_fingerprint")
        created_at = _normalize_utc(self.created_at, field_name="created_at")
        updated_at = _normalize_utc(self.updated_at, field_name="updated_at")
        if updated_at < created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.state == CommandExecutionState.IN_PROGRESS:
            if self.result_status is not None or self.result_payload_json is not None:
                raise ValueError("in-progress command records cannot contain a committed result")
        elif self.result_status is None or self.result_payload_json is None:
            raise ValueError("terminal command records require result_status and result_payload_json")
        elif not 100 <= self.result_status <= 599:
            raise ValueError("result_status must be a valid HTTP status code")
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)


@dataclass(frozen=True, slots=True)
class CommandIdempotencyClaim:
    record: CommandIdempotencyRecord
    created: bool


@dataclass(frozen=True, slots=True)
class CommandAuditRecord:
    audit_id: UUID
    request_id: UUID
    principal_id: str
    action: str
    outcome: CommandAuditOutcome
    created_at: datetime
    target_resource: str | None = None
    idempotency_key_hash: str | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.principal_id, field_name="principal_id")
        _require_text(self.action, field_name="action")
        if self.target_resource is not None:
            _require_text(self.target_resource, field_name="target_resource")
        if self.idempotency_key_hash is not None:
            _require_sha256(self.idempotency_key_hash, field_name="idempotency_key_hash")
        if self.error_code is not None:
            _require_text(self.error_code, field_name="error_code")
        object.__setattr__(self, "created_at", _normalize_utc(self.created_at, field_name="created_at"))


def _normalize_utc(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _require_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_sha256(value: str, *, field_name: str) -> None:
    if len(value) != 64:
        raise ValueError(f"{field_name} must contain 64 hex characters")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"{field_name} must be hexadecimal") from error
