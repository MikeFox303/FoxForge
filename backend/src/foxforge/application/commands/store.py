# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from typing import Protocol

from .models import CommandAuditRecord, CommandIdempotencyClaim, CommandIdempotencyRecord


class CommandStoreMissingError(RuntimeError):
    pass


class CommandIdempotencyStore(Protocol):
    def claim(self, record: CommandIdempotencyRecord) -> CommandIdempotencyClaim: ...

    def save(self, record: CommandIdempotencyRecord) -> None: ...

    def get(self, principal_id: str, operation: str, key_hash: str) -> CommandIdempotencyRecord | None: ...


class CommandAuditStore(Protocol):
    def append_audit(self, record: CommandAuditRecord) -> None: ...

    def list_audit(self) -> tuple[CommandAuditRecord, ...]: ...


class InMemoryCommandStore:
    """Deterministic non-durable command store for contract and service tests."""

    def __init__(self) -> None:
        self._idempotency: dict[tuple[str, str, str], CommandIdempotencyRecord] = {}
        self._audit: list[CommandAuditRecord] = []

    def claim(self, record: CommandIdempotencyRecord) -> CommandIdempotencyClaim:
        identity = (record.principal_id, record.operation, record.key_hash)
        existing = self._idempotency.get(identity)
        if existing is not None:
            return CommandIdempotencyClaim(record=existing, created=False)
        self._idempotency[identity] = record
        return CommandIdempotencyClaim(record=record, created=True)

    def save(self, record: CommandIdempotencyRecord) -> None:
        identity = (record.principal_id, record.operation, record.key_hash)
        if identity not in self._idempotency:
            raise CommandStoreMissingError(identity)
        self._idempotency[identity] = record

    def get(self, principal_id: str, operation: str, key_hash: str) -> CommandIdempotencyRecord | None:
        return self._idempotency.get((principal_id, operation, key_hash))

    def append_audit(self, record: CommandAuditRecord) -> None:
        self._audit.append(record)

    def list_audit(self) -> tuple[CommandAuditRecord, ...]:
        return tuple(sorted(self._audit, key=lambda record: (record.created_at, str(record.audit_id))))
