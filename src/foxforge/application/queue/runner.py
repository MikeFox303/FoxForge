# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

from foxforge.domain.printers import utc_now
from foxforge.domain.printers.models import normalize_utc

from .models import QueueEntry, QueueEntryState
from .service import QueueService


@dataclass(frozen=True, slots=True)
class QueueRetryPolicy:
    """Deterministic pre-start retry policy for queue dispatch failures."""

    initial_delay_seconds: float = 5.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 300.0
    max_attempts: int = 5

    def __post_init__(self) -> None:
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds must be non-negative")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max_delay_seconds must be at least initial_delay_seconds")
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")

    def delay_after_attempt(self, attempt_count: int) -> timedelta:
        if attempt_count <= 0:
            raise ValueError("attempt_count must be positive")
        seconds = self.initial_delay_seconds * (self.backoff_multiplier ** (attempt_count - 1))
        return timedelta(seconds=min(seconds, self.max_delay_seconds))


class QueueRunner:
    """Run one safe scheduling pass over printer-pinned queue entries.

    This is intentionally not a background loop. A future composition root can
    call ``run_once`` from a timer while tests can drive it deterministically.
    The runner never retries an ambiguous or receipt-bearing dispatch.
    """

    def __init__(self, queue: QueueService, *, retry_policy: QueueRetryPolicy | None = None) -> None:
        self._queue = queue
        self._retry_policy = retry_policy or QueueRetryPolicy()
        self._run_lock = asyncio.Lock()

    @property
    def retry_policy(self) -> QueueRetryPolicy:
        return self._retry_policy

    async def run_once(self, *, now: datetime | None = None) -> tuple[QueueEntry, ...]:
        async with self._run_lock:
            observed_now = normalize_utc(now or utc_now(), field_name="now")
            await self._queue.start()

            processed: list[QueueEntry] = []
            reserved_printers: set[str] = set()
            for entry in self._queue.list():
                if entry.printer_id in reserved_printers:
                    continue
                if not self._is_candidate(entry, observed_now):
                    continue

                reserved_printers.add(entry.printer_id)
                processed.append(await self._queue.dispatch(entry.queue_id))

            return tuple(processed)

    def _is_candidate(self, entry: QueueEntry, now: datetime) -> bool:
        if entry.receipt is not None:
            return False
        if entry.state in {QueueEntryState.PENDING, QueueEntryState.BLOCKED}:
            return True
        if entry.state != QueueEntryState.FAILED:
            return False

        error = entry.error
        if error is None or not error.retryable:
            return False
        if entry.attempt_count <= 0 or entry.last_attempt_at is None:
            return False
        if entry.attempt_count >= self._retry_policy.max_attempts:
            return False

        retry_at = entry.last_attempt_at + self._retry_policy.delay_after_attempt(entry.attempt_count)
        return now >= retry_at
