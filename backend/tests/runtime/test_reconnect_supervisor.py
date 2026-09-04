# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from foxforge.domain.printers import ConnectionState, OperationalState, PrinterSnapshot
from foxforge.runtime.reconnect import ReconnectPolicy, reconnect_backoff_seconds, run_connection_supervisor


class _ReconnectFleet:
    def __init__(self, printer_ids: tuple[str, ...]) -> None:
        self.ids = list(printer_ids)
        self.states = {printer_id: ConnectionState.DISCONNECTED for printer_id in printer_ids}
        self.attempts = {printer_id: 0 for printer_id in printer_ids}
        self.connected_events = {printer_id: asyncio.Event() for printer_id in printer_ids}
        self.blockers: dict[str, asyncio.Event] = {}
        self.failures_before_success: dict[str, int] = {}
        self.active_connects = 0
        self.max_active_connects = 0

    @property
    def printer_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.ids))

    def snapshot(self, printer_id: str) -> PrinterSnapshot:
        return PrinterSnapshot(
            printer_id=printer_id,
            connection=self.states[printer_id],
            operational_state=OperationalState.OFFLINE,
            active_job=None,
            observed_at=datetime.now(UTC),
            stale=self.states[printer_id] != ConnectionState.CONNECTED,
        )

    async def connect(self, printer_id: str) -> None:
        self.attempts[printer_id] += 1
        self.active_connects += 1
        self.max_active_connects = max(self.max_active_connects, self.active_connects)
        try:
            blocker = self.blockers.get(printer_id)
            if blocker is not None:
                await blocker.wait()
            remaining_failures = self.failures_before_success.get(printer_id, 0)
            if remaining_failures > 0:
                self.failures_before_success[printer_id] = remaining_failures - 1
                raise RuntimeError(f"synthetic reconnect failure for {printer_id}")
            self.states[printer_id] = ConnectionState.CONNECTED
            self.connected_events[printer_id].set()
        finally:
            self.active_connects -= 1


def _policy(*, max_concurrent: int = 4) -> ReconnectPolicy:
    return ReconnectPolicy(
        base_delay_seconds=0.005,
        max_delay_seconds=0.02,
        max_concurrent=max_concurrent,
        jitter_ratio=0,
        discovery_interval_seconds=0.002,
    )


def test_backoff_is_exponential_bounded_and_jittered() -> None:
    policy = ReconnectPolicy(
        base_delay_seconds=2,
        max_delay_seconds=10,
        max_concurrent=2,
        jitter_ratio=0.2,
        discovery_interval_seconds=1,
    )

    assert reconnect_backoff_seconds(policy, 1, random_value=0.5) == 2
    assert reconnect_backoff_seconds(policy, 2, random_value=0.5) == 4
    assert reconnect_backoff_seconds(policy, 3, random_value=0.5) == 8
    assert reconnect_backoff_seconds(policy, 4, random_value=0.5) == 10
    assert reconnect_backoff_seconds(policy, 1, random_value=0) == 1.6
    assert reconnect_backoff_seconds(policy, 1, random_value=1) == 2.4


def test_slow_printer_does_not_block_other_printer_recovery() -> None:
    async def scenario() -> None:
        fleet = _ReconnectFleet(("slow", "fast"))
        fleet.blockers["slow"] = asyncio.Event()
        supervisor = asyncio.create_task(run_connection_supervisor(fleet, _policy(max_concurrent=2)))
        try:
            await asyncio.wait_for(fleet.connected_events["fast"].wait(), timeout=0.2)
            assert fleet.states["fast"] == ConnectionState.CONNECTED
            assert fleet.states["slow"] == ConnectionState.DISCONNECTED
        finally:
            supervisor.cancel()
            await asyncio.gather(supervisor, return_exceptions=True)

    asyncio.run(scenario())


def test_global_reconnect_concurrency_is_bounded() -> None:
    async def scenario() -> None:
        fleet = _ReconnectFleet(tuple(f"printer-{index}" for index in range(5)))
        release = asyncio.Event()
        for printer_id in fleet.printer_ids:
            fleet.blockers[printer_id] = release

        supervisor = asyncio.create_task(run_connection_supervisor(fleet, _policy(max_concurrent=2)))
        try:
            for _ in range(100):
                if fleet.active_connects == 2:
                    break
                await asyncio.sleep(0.002)
            assert fleet.active_connects == 2
            assert fleet.max_active_connects == 2
            release.set()
            await asyncio.wait_for(
                asyncio.gather(*(event.wait() for event in fleet.connected_events.values())),
                timeout=0.2,
            )
            assert fleet.max_active_connects == 2
        finally:
            supervisor.cancel()
            await asyncio.gather(supervisor, return_exceptions=True)

    asyncio.run(scenario())


def test_failed_printer_recovers_independently_after_backoff() -> None:
    async def scenario() -> None:
        fleet = _ReconnectFleet(("recovering",))
        fleet.failures_before_success["recovering"] = 2
        supervisor = asyncio.create_task(
            run_connection_supervisor(
                fleet,
                _policy(),
                random_value=lambda: 0.5,
            )
        )
        try:
            await asyncio.wait_for(fleet.connected_events["recovering"].wait(), timeout=0.2)
            assert fleet.attempts["recovering"] == 3
            assert fleet.states["recovering"] == ConnectionState.CONNECTED
        finally:
            supervisor.cancel()
            await asyncio.gather(supervisor, return_exceptions=True)

    asyncio.run(scenario())


def test_dynamic_printer_is_discovered_without_restarting_supervisor() -> None:
    async def scenario() -> None:
        fleet = _ReconnectFleet(())
        supervisor = asyncio.create_task(run_connection_supervisor(fleet, _policy()))
        try:
            await asyncio.sleep(0.005)
            fleet.ids.append("new-printer")
            fleet.states["new-printer"] = ConnectionState.DISCONNECTED
            fleet.attempts["new-printer"] = 0
            fleet.connected_events["new-printer"] = asyncio.Event()
            await asyncio.wait_for(fleet.connected_events["new-printer"].wait(), timeout=0.2)
            assert fleet.attempts["new-printer"] == 1
        finally:
            supervisor.cancel()
            await asyncio.gather(supervisor, return_exceptions=True)

    asyncio.run(scenario())
