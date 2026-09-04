# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class CommandIdempotencyState(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class CommandIdempotencyRecord:
    """Durable reservation for one authenticated command replay identity."""

    principal_id: str
    operation: str
    idempotency_key: str
    request_fingerprint: str
    state: CommandIdempotencyState
    created_at: datetime
    updated_at: datetime
    result_ref: str | None = None
    outcome_code: str | None = None

    def __post_init__(self) -> None:
        _validate_nonempty(self.principal_id, field_name="principal_id")
        _validate_nonempty(self.operation, field_name="operation")
        _validate_idempotency_key(self.idempotency_key)
        _validate_fingerprint(self.request_fingerprint)

        created_at = _normalize_utc(self.created_at, field_name="created_at")
        updated_at = _normalize_utc(self.updated_at, field_name="updated_at")
        if updated_at < created_at:
            raise ValueError("updated_at must not be before created_at")
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

        if self.state == CommandIdempotencyState.STARTED:
            if self.result_ref is not None or self.outcome_code is not None:
                raise ValueError("started command idempotency record cannot contain a terminal result")
            return

        if self.outcome_code is None or not self.outcome_code.strip():
            raise ValueError("completed command idempotency record requires outcome_code")


def command_request_fingerprint(payload: object) -> str:
    """Return a deterministic SHA-256 fingerprint for a JSON command payload."""

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_nonempty(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _validate_idempotency_key(value: str) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise ValueError("idempotency_key must contain 1 to 128 visible ASCII characters")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in value):
        raise ValueError("idempotency_key must contain visible ASCII characters only")


def _validate_fingerprint(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError("request_fingerprint must contain 64 hexadecimal characters")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError("request_fingerprint must be hexadecimal") from error


def _normalize_utc(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)
