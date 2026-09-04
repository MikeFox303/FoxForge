# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
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
    """One append-only security audit observation for a command request."""

    request_id: str
    action: str
    outcome: CommandAuditOutcome
    occurred_at: datetime
    principal_id: str | None = None
    target_ref: str | None = None
    idempotency_key_digest: str | None = None
    error_code: str | None = None
    audit_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty")
        if not self.action.strip():
            raise ValueError("action must not be empty")
        if self.principal_id is not None and not self.principal_id.strip():
            raise ValueError("principal_id must not be empty when present")
        if self.target_ref is not None and not self.target_ref.strip():
            raise ValueError("target_ref must not be empty when present")
        if self.error_code is not None and not self.error_code.strip():
            raise ValueError("error_code must not be empty when present")
        if self.idempotency_key_digest is not None:
            digest = self.idempotency_key_digest.lower()
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ValueError("idempotency_key_digest must be a SHA-256 hexadecimal digest")
            object.__setattr__(self, "idempotency_key_digest", digest)
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        object.__setattr__(self, "occurred_at", self.occurred_at.astimezone(UTC))


class CommandAuditStore(Protocol):
    def append(self, record: CommandAuditRecord) -> None: ...

    def list_for_request(self, request_id: str) -> tuple[CommandAuditRecord, ...]: ...


class InMemoryCommandAuditStore:
    """Deterministic append-only audit store for API/application tests."""

    def __init__(self) -> None:
        self._records: list[CommandAuditRecord] = []

    def append(self, record: CommandAuditRecord) -> None:
        self._records.append(record)

    def list_for_request(self, request_id: str) -> tuple[CommandAuditRecord, ...]:
        return tuple(record for record in self._records if record.request_id == request_id)

    def list(self) -> tuple[CommandAuditRecord, ...]:
        return tuple(self._records)


def command_idempotency_key_digest(value: str | None) -> str | None:
    if value is None or not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
