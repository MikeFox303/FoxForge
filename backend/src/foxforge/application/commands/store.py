# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from .models import CommandIdempotencyRecord, CommandIdempotencyReservation, CommandIdempotencyState


class CommandIdempotencyConflictError(RuntimeError):
    pass


class CommandIdempotencyMissingError(KeyError):
    pass


class CommandIdempotencyStore(Protocol):
    def reserve(self, record: CommandIdempotencyRecord) -> CommandIdempotencyReservation: ...

    def complete(
        self,
        *,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        request_fingerprint: str,
        outcome_code: str,
        result_ref: str | None = None,
        completed_at: datetime | None = None,
    ) -> CommandIdempotencyRecord: ...

    def get(
        self,
        principal_id: str,
        operation: str,
        idempotency_key: str,
    ) -> CommandIdempotencyRecord | None: ...


class InMemoryCommandIdempotencyStore:
    """Deterministic command-idempotency store used by tests/composition."""

    def __init__(self) -> None:
        self._records: dict[tuple[Hashable, ...], CommandIdempotencyRecord] = {}

    def reserve(self, record: CommandIdempotencyRecord) -> CommandIdempotencyReservation:
        key = _record_key(record.principal_id, record.operation, record.idempotency_key)
        existing = self._records.get(key)
        if existing is None:
            self._records[key] = record
            return CommandIdempotencyReservation(record=record, created=True)
        _require_same_fingerprint(existing, record.request_fingerprint)
        return CommandIdempotencyReservation(record=existing, created=False)

    def complete(
        self,
        *,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        request_fingerprint: str,
        outcome_code: str,
        result_ref: str | None = None,
        completed_at: datetime | None = None,
    ) -> CommandIdempotencyRecord:
        key = _record_key(principal_id, operation, idempotency_key)
        existing = self._records.get(key)
        if existing is None:
            raise CommandIdempotencyMissingError(key)
        _require_same_fingerprint(existing, request_fingerprint)

        if existing.state == CommandIdempotencyState.COMPLETED:
            if existing.outcome_code == outcome_code and existing.result_ref == result_ref:
                return existing
            raise CommandIdempotencyConflictError("completed idempotency record has a different terminal result")

        completed = replace(
            existing,
            state=CommandIdempotencyState.COMPLETED,
            outcome_code=outcome_code,
            result_ref=result_ref,
            updated_at=completed_at or datetime.now(UTC),
        )
        self._records[key] = completed
        return completed

    def get(
        self,
        principal_id: str,
        operation: str,
        idempotency_key: str,
    ) -> CommandIdempotencyRecord | None:
        return self._records.get(_record_key(principal_id, operation, idempotency_key))


def _record_key(principal_id: str, operation: str, idempotency_key: str) -> tuple[str, str, str]:
    return principal_id, operation, idempotency_key


def _require_same_fingerprint(record: CommandIdempotencyRecord, request_fingerprint: str) -> None:
    if record.request_fingerprint != request_fingerprint:
        raise CommandIdempotencyConflictError("idempotency key was already used with a different request")
