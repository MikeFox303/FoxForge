# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from .models import FilamentReservation


class FilamentAccountingStoreConflictError(RuntimeError):
    pass


class FilamentAccountingStoreMissingError(RuntimeError):
    pass


class FilamentAccountingStore(Protocol):
    def create(self, reservation: FilamentReservation) -> None: ...

    def save(self, reservation: FilamentReservation) -> None: ...

    def get(self, queue_id: UUID, material_index: int) -> FilamentReservation | None: ...

    def list_for_queue(self, queue_id: UUID) -> tuple[FilamentReservation, ...]: ...

    def list_for_spool(self, spool_id: UUID) -> tuple[FilamentReservation, ...]: ...

    def list(self) -> tuple[FilamentReservation, ...]: ...


class InMemoryFilamentAccountingStore:
    def __init__(self) -> None:
        self._items: dict[tuple[UUID, int], FilamentReservation] = {}

    def create(self, reservation: FilamentReservation) -> None:
        key = (reservation.queue_id, reservation.material_index)
        if key in self._items:
            raise FilamentAccountingStoreConflictError(
                f"reservation already exists: {reservation.queue_id}/{reservation.material_index}"
            )
        self._items[key] = reservation

    def save(self, reservation: FilamentReservation) -> None:
        key = (reservation.queue_id, reservation.material_index)
        if key not in self._items:
            raise FilamentAccountingStoreMissingError(
                f"reservation does not exist: {reservation.queue_id}/{reservation.material_index}"
            )
        self._items[key] = reservation

    def get(self, queue_id: UUID, material_index: int) -> FilamentReservation | None:
        return self._items.get((queue_id, material_index))

    def list_for_queue(self, queue_id: UUID) -> tuple[FilamentReservation, ...]:
        return tuple(
            sorted(
                (item for item in self._items.values() if item.queue_id == queue_id),
                key=lambda item: item.material_index,
            )
        )

    def list_for_spool(self, spool_id: UUID) -> tuple[FilamentReservation, ...]:
        return tuple(
            sorted(
                (item for item in self._items.values() if item.spool_id == spool_id),
                key=lambda item: (item.created_at, str(item.queue_id), item.material_index),
            )
        )

    def list(self) -> tuple[FilamentReservation, ...]:
        return tuple(
            sorted(
                self._items.values(),
                key=lambda item: (item.created_at, str(item.queue_id), item.material_index),
            )
        )
