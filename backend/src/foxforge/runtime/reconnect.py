# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from foxforge.application.fleet import FleetPrinterNotFoundError
from foxforge.domain.printers import ConnectionState, PrinterAdapterError

_LOG = logging.getLogger(__name__)


class ReconnectFleet(Protocol):
    @property
    def printer_ids(self) -> tuple[str, ...]: ...

    def snapshot(self, printer_id: str): ...

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
) -> None:
    """Maintain independent reconnect workers for the current dynamic fleet."""

    semaphore = asyncio.Semaphore(policy.max_concurrent)
    workers: dict[str, asyncio.Task[None]] = {}
    try:
        while True:
            current = set(fleet.printer_ids)

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
            consecutive_failures = 0
            await asyncio.sleep(policy.base_delay_seconds)
            continue

        try:
            async with semaphore:
                if printer_id not in fleet.printer_ids:
                    return
                if fleet.snapshot(printer_id).connection != ConnectionState.DISCONNECTED:
                    consecutive_failures = 0
                    await asyncio.sleep(policy.base_delay_seconds)
                    continue
                await fleet.connect(printer_id)
        except asyncio.CancelledError:
            raise
        except FleetPrinterNotFoundError:
            return
        except PrinterAdapterError as error:
            consecutive_failures += 1
            _LOG.warning(
                "printer %s remains offline: %s (%s); reconnect attempt %d",
                printer_id,
                error.message,
                error.code.value,
                consecutive_failures,
            )
        except Exception:
            consecutive_failures += 1
            _LOG.exception(
                "unexpected connection failure for printer %s; reconnect attempt %d",
                printer_id,
                consecutive_failures,
            )
        else:
            consecutive_failures = 0

        delay = reconnect_backoff_seconds(
            policy,
            consecutive_failures,
            random_value=random_value(),
        )
        await asyncio.sleep(delay)
