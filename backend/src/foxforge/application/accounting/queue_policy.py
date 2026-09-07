# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from uuid import UUID

from foxforge.application.inventory import InventoryBalanceError, InventoryService, SpoolNotFoundError
from foxforge.application.queue.models import QueueEntry
from foxforge.application.queue.policy import QueueDispatchGateResult
from foxforge.domain.printers.capabilities import PrintAssessmentBlocker, PrintAssessmentBlockerCode

from .models import FilamentReservation, FilamentReservationState
from .service import FilamentAccountingService


class FilamentAccountingQueuePolicy:
    """Queue integration boundary for automatic filament accounting.

    The policy is vendor-independent. Routing/toolhead safety remains owned by
    QueueService's fresh routing compiler; this layer validates only durable
    accounting evidence immediately before the queue crosses DISPATCHING.
    """

    def __init__(self, accounting: FilamentAccountingService, inventory: InventoryService) -> None:
        self._accounting = accounting
        self._inventory = inventory

    def assess_dispatch(self, entry: QueueEntry) -> QueueDispatchGateResult:
        bindings = {binding.material_index: binding for binding in entry.request.material_bindings}
        reservations = self._accounting.reservations_for_queue(entry.queue_id)
        by_index = {reservation.material_index: reservation for reservation in reservations}

        if not bindings:
            if reservations:
                return _blocked(
                    PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID,
                    "accounting reservations exist for a request with no material bindings",
                )
            return QueueDispatchGateResult()

        if set(by_index) != set(bindings):
            return _blocked(
                PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID,
                "automatic accounting plan must cover every material binding exactly once",
            )

        blockers: list[PrintAssessmentBlocker] = []
        spool_ids: set[UUID] = set()
        for material_index in sorted(bindings):
            binding = bindings[material_index]
            reservation = by_index[material_index]
            blocker = self._reservation_blocker(entry, reservation, binding.slot_id)
            if blocker is not None:
                blockers.append(blocker)
                continue
            spool_ids.add(reservation.spool_id)

        if blockers:
            return QueueDispatchGateResult(tuple(blockers))

        for spool_id in sorted(spool_ids, key=str):
            try:
                remaining = self._inventory.balance(spool_id).remaining_filament_mass_g
            except (SpoolNotFoundError, InventoryBalanceError) as error:
                blockers.append(
                    PrintAssessmentBlocker(
                        PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                        f"reserved spool {spool_id} cannot provide a valid current balance: {error}",
                    )
                )
                continue
            held = self._accounting.reserved_mass(spool_id)
            if held > remaining:
                blockers.append(
                    PrintAssessmentBlocker(
                        PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                        f"reserved spool {spool_id} has {remaining} g remaining but {held} g is actively held",
                    )
                )

        return QueueDispatchGateResult(tuple(blockers))

    def sync_queue_entry(self, entry: QueueEntry) -> object:
        return self._accounting.sync_queue_entry(entry)

    def _reservation_blocker(
        self,
        entry: QueueEntry,
        reservation: FilamentReservation,
        slot_id: str,
    ) -> PrintAssessmentBlocker | None:
        if reservation.state != FilamentReservationState.RESERVED:
            return PrintAssessmentBlocker(
                PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                f"material {reservation.material_index} reservation is {reservation.state.value}, not reserved",
            )
        if reservation.printer_id != entry.printer_id or reservation.slot_id != slot_id:
            return PrintAssessmentBlocker(
                PrintAssessmentBlockerCode.MATERIAL_BINDING_INVALID,
                (
                    f"material {reservation.material_index} reservation no longer matches "
                    "the freshly compiled physical source"
                ),
            )

        assignment = self._inventory.assignment_for_slot(entry.printer_id, slot_id)
        if assignment is None:
            return PrintAssessmentBlocker(
                PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                f"material {reservation.material_index} physical source no longer has an assigned FoxForge spool",
            )
        if assignment.spool_id != reservation.spool_id:
            return PrintAssessmentBlocker(
                PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                f"material {reservation.material_index} physical source is now assigned to a different spool",
            )

        try:
            spool = self._inventory.get_spool(reservation.spool_id)
        except SpoolNotFoundError as error:
            return PrintAssessmentBlocker(
                PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                f"reserved spool no longer exists: {error}",
            )
        if spool.archived:
            return PrintAssessmentBlocker(
                PrintAssessmentBlockerCode.MATERIAL_SOURCE_UNAVAILABLE,
                "archived spool cannot satisfy an automatic accounting reservation",
            )
        return None


def _blocked(code: PrintAssessmentBlockerCode, message: str) -> QueueDispatchGateResult:
    return QueueDispatchGateResult((PrintAssessmentBlocker(code, message),))
