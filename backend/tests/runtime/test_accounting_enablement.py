# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from foxforge.application.fleet import FleetService
from foxforge.application.queue import QueueDispatchGateResult, QueueEntry
from foxforge.domain.printers import PrinterAdapter, PrinterIdentity
from foxforge.domain.printers.capabilities import PrintAssessmentBlocker, PrintAssessmentBlockerCode
from foxforge.runtime.accounting_enablement import (
    FILAMENT_ACCOUNTING_MODE_BAMBU_VALIDATION,
    FILAMENT_ACCOUNTING_MODE_DISABLED,
    ProviderScopedQueuePreDispatchGate,
    enabled_accounting_adapter_kinds,
)


class _RecordingGate:
    def __init__(self, result: QueueDispatchGateResult) -> None:
        self.result = result
        self.calls: list[str] = []

    def assess_dispatch(self, entry: QueueEntry) -> QueueDispatchGateResult:
        self.calls.append(entry.printer_id)
        return self.result


def _identity(printer_id: str, adapter_kind: str) -> PrinterIdentity:
    return PrinterIdentity(
        printer_id=printer_id,
        display_name=printer_id,
        vendor="test",
        model="test",
        serial_number=None,
        adapter_kind=adapter_kind,
    )


def _fleet(*identities: PrinterIdentity) -> FleetService:
    adapters = tuple(cast(PrinterAdapter, SimpleNamespace(identity=identity)) for identity in identities)
    return FleetService(adapters)


def _entry(printer_id: str) -> QueueEntry:
    return cast(QueueEntry, SimpleNamespace(printer_id=printer_id))


def test_candidate6_accounting_modes_are_explicit_and_bambu_only() -> None:
    assert enabled_accounting_adapter_kinds(FILAMENT_ACCOUNTING_MODE_DISABLED) == frozenset()
    assert enabled_accounting_adapter_kinds(FILAMENT_ACCOUNTING_MODE_BAMBU_VALIDATION) == frozenset({"bambu"})
    with pytest.raises(ValueError, match="unsupported filament accounting mode"):
        enabled_accounting_adapter_kinds("moonraker-validation")


def test_provider_scoped_gate_delegates_only_for_enabled_bambu_adapter() -> None:
    blocked = QueueDispatchGateResult(
        (
            PrintAssessmentBlocker(
                PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                "accounting evidence missing",
            ),
        )
    )
    delegate = _RecordingGate(blocked)
    gate = ProviderScopedQueuePreDispatchGate(
        _fleet(_identity("x2d", "bambu"), _identity("ender", "moonraker")),
        delegate,
        enabled_adapter_kinds={"bambu"},
    )

    assert gate.assess_dispatch(_entry("x2d")) == blocked
    assert gate.assess_dispatch(_entry("ender")).allowed is True
    assert delegate.calls == ["x2d"]


def test_provider_scoped_gate_fails_closed_if_printer_identity_disappears() -> None:
    delegate = _RecordingGate(QueueDispatchGateResult())
    gate = ProviderScopedQueuePreDispatchGate(
        _fleet(_identity("x2d", "bambu")),
        delegate,
        enabled_adapter_kinds={"bambu"},
    )

    result = gate.assess_dispatch(_entry("missing"))

    assert result.allowed is False
    assert result.blockers[0].code == PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE
    assert delegate.calls == []


def test_provider_scoped_gate_rejects_empty_enablement_set() -> None:
    with pytest.raises(ValueError, match="enabled_adapter_kinds"):
        ProviderScopedQueuePreDispatchGate(
            _fleet(_identity("x2d", "bambu")),
            _RecordingGate(QueueDispatchGateResult()),
            enabled_adapter_kinds=set(),
        )
