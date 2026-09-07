# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from foxforge.domain.printers.capabilities import PrintAssessmentBlocker

from .models import QueueEntry


@dataclass(frozen=True, slots=True)
class QueueDispatchGateResult:
    blockers: tuple[PrintAssessmentBlocker, ...] = ()

    @property
    def allowed(self) -> bool:
        return not self.blockers


class QueuePreDispatchGate(Protocol):
    """Optional common policy evaluated after fresh assessment but before DISPATCHING."""

    def assess_dispatch(self, entry: QueueEntry) -> QueueDispatchGateResult: ...


class QueueLifecycleObserver(Protocol):
    """Optional observer for one durable queue-state change or restart replay."""

    def sync_queue_entry(self, entry: QueueEntry) -> object: ...
