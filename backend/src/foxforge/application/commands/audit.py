# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4


class CommandAuditOutcome(StrEnum):
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CONFLICT = "conflict"
    DENIED = "denied"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CommandAuditRecord:
    audit_id: UUID
    request_id: str
    principal_id: str
    action: str
    outcome: CommandAuditOutcome
    created_at: datetime
    target_resource: str | None = None
    idempotency_key_digest: str | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("request_id", self.request_id),
            ("principal_id", self.principal_id),
            ("action", self.action),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.target_resource is not None and not self.target_resource.strip():
            raise ValueError("target_resource must be non-empty when provided")
        if self.error_code is not None and not self.error_code.strip():
            raise ValueError("error_code must be non-empty when provided")
        if self.idempotency_key_digest is not None:
            _validate_sha256(self.idempotency_key_digest)
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))


class CommandAuditStore(Protocol):
    def append(self, record: CommandAuditRecord) -> None: ...

    def list(self) -> tuple[CommandAuditRecord, ...]: ...


class InMemoryCommandAuditStore:
    def __init__(self) -> None:
        self._records: list[CommandAuditRecord] = []

    def append(self, record: CommandAuditRecord) -> None:
        self._records.append(record)

    def list(self) -> tuple[CommandAuditRecord, ...]:
        return tuple(sorted(self._records, key=lambda record: (record.created_at, str(record.audit_id))))


def new_command_audit_record(
    *,
    request_id: str,
    principal_id: str,
    action: str,
    outcome: CommandAuditOutcome,
    target_resource: str | None = None,
    idempotency_key: str | None = None,
    error_code: str | None = None,
    created_at: datetime | None = None,
) -> CommandAuditRecord:
    return CommandAuditRecord(
        audit_id=uuid4(),
        request_id=request_id,
        principal_id=principal_id,
        action=action,
        outcome=outcome,
        target_resource=target_resource,
        idempotency_key_digest=(None if idempotency_key is None else command_idempotency_digest(idempotency_key)),
        error_code=error_code,
        created_at=(created_at or datetime.now(UTC)),
    )


def command_idempotency_digest(idempotency_key: str) -> str:
    if not isinstance(idempotency_key, str) or not idempotency_key:
        raise ValueError("idempotency_key must be a non-empty string")
    return hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()


def _validate_sha256(value: str) -> None:
    if len(value) != 64:
        raise ValueError("idempotency_key_digest must contain 64 hexadecimal characters")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError("idempotency_key_digest must be hexadecimal") from error
