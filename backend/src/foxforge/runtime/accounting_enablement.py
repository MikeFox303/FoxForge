# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Collection

from foxforge.application.fleet import FleetService
from foxforge.application.queue import QueueDispatchGateResult, QueueEntry, QueuePreDispatchGate
from foxforge.domain.printers.capabilities import PrintAssessmentBlocker, PrintAssessmentBlockerCode

FILAMENT_ACCOUNTING_MODE_DISABLED = "disabled"
FILAMENT_ACCOUNTING_MODE_BAMBU_VALIDATION = "bambu-validation"
FILAMENT_ACCOUNTING_MODES = frozenset(
    {
        FILAMENT_ACCOUNTING_MODE_DISABLED,
        FILAMENT_ACCOUNTING_MODE_BAMBU_VALIDATION,
    }
)


class ProviderScopedQueuePreDispatchGate:
    """Delegate a queue gate only for explicitly enabled adapter kinds.

    Provider selection belongs in runtime composition, not the accounting
    application package. Candidate 6 uses this seam to make the immutable image
    validation-capable while leaving automatic enforcement disabled by default.
    """

    def __init__(
        self,
        fleet: FleetService,
        delegate: QueuePreDispatchGate,
        *,
        enabled_adapter_kinds: Collection[str],
    ) -> None:
        kinds = frozenset(kind.strip() for kind in enabled_adapter_kinds if kind.strip())
        if not kinds:
            raise ValueError("enabled_adapter_kinds must contain at least one adapter kind")
        self._fleet = fleet
        self._delegate = delegate
        self._enabled_adapter_kinds = kinds

    def assess_dispatch(self, entry: QueueEntry) -> QueueDispatchGateResult:
        identity = next(
            (candidate for candidate in self._fleet.identities() if candidate.printer_id == entry.printer_id),
            None,
        )
        if identity is None:
            return QueueDispatchGateResult(
                (
                    PrintAssessmentBlocker(
                        PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                        "printer identity disappeared before provider-scoped accounting validation",
                    ),
                )
            )
        if identity.adapter_kind not in self._enabled_adapter_kinds:
            return QueueDispatchGateResult()
        return self._delegate.assess_dispatch(entry)


def enabled_accounting_adapter_kinds(mode: str) -> frozenset[str]:
    if mode == FILAMENT_ACCOUNTING_MODE_DISABLED:
        return frozenset()
    if mode == FILAMENT_ACCOUNTING_MODE_BAMBU_VALIDATION:
        return frozenset({"bambu"})
    raise ValueError(f"unsupported filament accounting mode: {mode}")
