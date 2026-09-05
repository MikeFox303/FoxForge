# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Protocol

from foxforge.application.fleet import FleetPrinterNotFoundError
from foxforge.domain.printers import (
    ConnectionState,
    PrinterAdapterError,
    PrinterErrorCode,
    PrinterSnapshot,
    utc_now,
)

_LOG = logging.getLogger(__name__)


class ReconnectFleet(Protocol):
    @property
    def printer_ids(self) -> tuple[str, ...]: ...

    def snapshot(self, printer_id: str) -> PrinterSnapshot: ...

    async def connect(self, printer_id: str) -> None: ...


@dataclass(frozen=True, slots=True)
class ReconnectPolicy:
    base_delay_seconds: float
    max_delay_seconds: float
    max_concurrent: int = 4
    jitter_ratio: float = 0.2
    discovery_interval_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.base_delay_seconds <= 0:
            raise ValueError("base_delay_seconds must be positive")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must be at least base_delay_seconds")
        if self.max_concurrent <= 0:
            raise ValueError("max_concurrent must be positive")
        if not 0 <= self.jitter_ratio <= 1:
            raise ValueError("jitter_ratio must be between 0 and 1")
        if self.discovery_interval_seconds <= 0:
            raise ValueError("discovery_interval_seconds must be positive")


@dataclass(frozen=True, slots=True)
class ReconnectPrinterStatus:
    """Sanitized reconnect context for operator diagnostics.

    Raw adapter exception messages and vendor codes deliberately do not cross
    this runtime boundary. The registry keeps only normalized FoxForge error
    categories, retryability and timing information.
    """

    printer_id: str
    consecutive_failures: int = 0
    last_attempt_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_error_code: PrinterErrorCode | None = None
    last_error_retryable: bool | None = None
    next_retry_at: datetime | None = None
    recovered_at: datetime | None = None


class ReconnectDiagnostics:
    """In-memory, secret-safe reconnect state owned by one runtime process."""

    def __init__(self) -> None:
        self._statuses: dict[str, ReconnectPrinterStatus] = {}

    def statuses(self) -> tuple[ReconnectPrinterStatus, ...]:
        return tuple(self._statuses[key] for key in sorted(self._statuses))

    def retain(self, printer_ids: set[str]) -> None:
        for printer_id in tuple(self._statuses):
            if printer_id not in printer_ids:
                self._statuses.pop(printer_id, None)

    def record_attempt(self, printer_id: str) -> None:
        current = self._statuses.get(printer_id, ReconnectPrinterStatus(printer_id=printer_id))
        self._statuses[printer_id] = replace(current, last_attempt_at=utc_now())

    def record_failure(
        self,
        printer_id: str,
        *,
        consecutive_failures: int,
        error_code: PrinterErrorCode,
        retryable: bool,
        retry_delay_seconds: float,
    ) -> None:
        now = utc_now()
        current = self._statuses.get(printer_id, ReconnectPrinterStatus(printer_id=printer_id))
        self._statuses[printer_id] = replace(
            current,
            consecutive_failures=consecutive_failures,
            last_failure_at=now,
            last_error_code=error_code,
            last_error_retryable=retryable,
            next_retry_at=now + timedelta(seconds=retry_delay_seconds),
        )

    def record_recovered(self, printer_id: str) -> None:
        current = self._statuses.get(printer_id)
        if current is None:
            return
        self._statuses[printer_id] = replace(
            current,
            consecutive_failures=0,
            next_retry_at=None,
            recovered_at=utc_now(),
        )


def default_reconnect_policy(base_delay_seconds: float) -> ReconnectPolicy:
    return ReconnectPolicy(
        base_delay_seconds=base_delay_seconds,
        max_delay_seconds=max(base_delay_seconds, base_delay_seconds * 8),
        discovery_interval_seconds=min(base_delay_seconds, 1.0),
    )


def reconnect_backoff_seconds(
    policy: ReconnectPolicy,
    consecutive_failures: int,
    *,
    random_value: float,
) -> float:
    if consecutive_failures <= 0:
        return policy.base_delay_seconds
    if not 0 <= random_value <= 1:
        raise ValueError("random_value must be between 0 and 1")

    exponent = min(consecutive_failures - 1, 30)
    raw = min(policy.max_delay_seconds, policy.base_delay_seconds * (2**exponent))
    jitter_factor = 1 + ((random_value * 2 - 1) * policy.jitter_ratio)
    return min(policy.max_delay_seconds, max(0.0, raw * jitter_factor))


async def run_connection_supervisor(
    fleet: ReconnectFleet,
    policy: ReconnectPolicy,
    *,
    random_value: Callable[[], float] = random.random,
    diagnostics: ReconnectDiagnostics | None = None,
) -> None:
    """Maintain independent reconnect workers for the current dynamic fleet."""

    semaphore = asyncio.Semaphore(policy.max_concurrent)
    workers: dict[str, asyncio.Task[None]] = {}
    try:
        while True:
            current = set(fleet.printer_ids)
            if diagnostics is not None:
                diagnostics.retain(current)

            for printer_id in tuple(workers):
                if printer_id in current and not workers[printer_id].done():
                    continue
                task = workers.pop(printer_id)
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)

            for printer_id in sorted(current - set(workers)):
                workers[printer_id] = asyncio.create_task(
                    _reconnect_worker(
                        fleet,
                        printer_id,
                        policy,
                        semaphore,
                        random_value=random_value,
                        diagnostics=diagnostics,
                    ),
                    name=f"foxforge-reconnect-{printer_id}",
                )

            await asyncio.sleep(policy.discovery_interval_seconds)
    finally:
        for task in workers.values():
            task.cancel()
        if workers:
            await asyncio.gather(*workers.values(), return_exceptions=True)


async def _reconnect_worker(
    fleet: ReconnectFleet,
    printer_id: str,
    policy: ReconnectPolicy,
    semaphore: asyncio.Semaphore,
    *,
    random_value: Callable[[], float],
    diagnostics: ReconnectDiagnostics | None,
) -> None:
    consecutive_failures = 0
    while True:
        if printer_id not in fleet.printer_ids:
            return

        try:
            snapshot = fleet.snapshot(printer_id)
        except FleetPrinterNotFoundError:
            return

        if snapshot.connection != ConnectionState.DISCONNECTED:
            if consecutive_failures > 0 and diagnostics is not None:
                diagnostics.record_recovered(printer_id)
            consecutive_failures = 0
            await asyncio.sleep(policy.base_delay_seconds)
            continue

        already_recovered = False
        connection_error: PrinterAdapterError | None = None
        unexpected_failure = False
        if diagnostics is not None:
            diagnostics.record_attempt(printer_id)
        try:
            async with semaphore:
                if printer_id not in fleet.printer_ids:
                    return
                if fleet.snapshot(printer_id).connection != ConnectionState.DISCONNECTED:
                    consecutive_failures = 0
                    already_recovered = True
                else:
                    await fleet.connect(printer_id)
        except asyncio.CancelledError:
            raise
        except FleetPrinterNotFoundError:
            return
        except PrinterAdapterError as error:
            consecutive_failures += 1
            connection_error = error
            _LOG.warning(
                "printer %s remains offline: %s (%s); reconnect attempt %d",
                printer_id,
                error.message,
                error.code.value,
                consecutive_failures,
            )
        except Exception:
            consecutive_failures += 1
            unexpected_failure = True
            _LOG.exception(
                "unexpected connection failure for printer %s; reconnect attempt %d",
                printer_id,
                consecutive_failures,
            )
        else:
            consecutive_failures = 0
            if diagnostics is not None:
                diagnostics.record_recovered(printer_id)

        if already_recovered:
            if diagnostics is not None:
                diagnostics.record_recovered(printer_id)
            await asyncio.sleep(policy.base_delay_seconds)
            continue

        delay = reconnect_backoff_seconds(
            policy,
            consecutive_failures,
            random_value=random_value(),
        )
        if diagnostics is not None and consecutive_failures > 0:
            if connection_error is not None:
                diagnostics.record_failure(
                    printer_id,
                    consecutive_failures=consecutive_failures,
                    error_code=connection_error.code,
                    retryable=connection_error.retryable,
                    retry_delay_seconds=delay,
                )
            elif unexpected_failure:
                diagnostics.record_failure(
                    printer_id,
                    consecutive_failures=consecutive_failures,
                    error_code=PrinterErrorCode.INTERNAL_ADAPTER_ERROR,
                    retryable=True,
                    retry_delay_seconds=delay,
                )
        await asyncio.sleep(delay)
