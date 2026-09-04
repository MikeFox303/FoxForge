# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from typing import Protocol

from .models import CommandAuditRecord, CommandIdempotencyClaim, CommandIdempotencyRecord


class CommandIdempotencyStore(Protocol):
    def claim(self, record: CommandIdempotencyRecord) -> CommandIdempotencyClaim: ...

    def save(self, record: CommandIdempotencyRecord) -> None: ...

    def get(self, principal_id: str, operation: str, key_hash: str) -> CommandIdempotencyRecord | None: ...


class CommandAuditStore(Protocol):
    def append_audit(self, record: CommandAuditRecord) -> None: ...

    def list_audit(self) -> tuple[CommandAuditRecord, ...]: ...
