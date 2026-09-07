# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from threading import RLock
from typing import Protocol
from uuid import UUID

from .models import FilamentReservation


class FilamentAccountingStoreConflictError(RuntimeError):
    pass


class FilamentAccountingStoreMissingError(RuntimeError):
    pass


class FilamentAccountingStore(Protocol):
    def create(self, reservation: FilamentReservation) -> None: ...

    def create_many(self, reservations: tuple[FilamentReservation, ...]) -> None: ...

    def save(self, reservation: FilamentReservation) -> None: ...

    def get(self, queue_id: UUID, material_index: int) -> FilamentReservation | None: ...

    def list_for_queue(self, queue_id: UUID) -> tuple[FilamentReservation, ...]: ...

    def list_for_spool(self, spool_id: UUID) -> tuple[FilamentReservation, ...]: ...

    def list(self) -> tuple[FilamentReservation, ...]: ...


class InMemoryFilamentAccountingStore:
    def __init__(self) -> None:
        self._items: dict[tuple[UUID, int], FilamentReservation] = {}
        self._lock = RLock()

    def create(self, reservation: FilamentReservation) -> None:
        self.create_many((reservation,))

    def create_many(self, reservations: tuple[FilamentReservation, ...]) -> None:
        if not reservations:
            return
        keys = [(item.queue_id, item.material_index) for item in reservations]
        if len(keys) != len(set(keys)):
            raise FilamentAccountingStoreConflictError("reservation batch contains duplicate queue/material keys")
        with self._lock:
            conflict = next((key for key in keys if key in self._items), None)
            if conflict is not None:
                raise FilamentAccountingStoreConflictError(f"reservation already exists: {conflict[0]}/{conflict[1]}")
            for reservation in reservations:
                self._items[(reservation.queue_id, reservation.material_index)] = reservation

    def save(self, reservation: FilamentReservation) -> None:
        key = (reservation.queue_id, reservation.material_index)
        with self._lock:
            if key not in self._items:
                raise FilamentAccountingStoreMissingError(
                    f"reservation does not exist: {reservation.queue_id}/{reservation.material_index}"
                )
            self._items[key] = reservation

    def get(self, queue_id: UUID, material_index: int) -> FilamentReservation | None:
        with self._lock:
            return self._items.get((queue_id, material_index))

    def list_for_queue(self, queue_id: UUID) -> tuple[FilamentReservation, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (item for item in self._items.values() if item.queue_id == queue_id),
                    key=lambda item: item.material_index,
                )
            )

    def list_for_spool(self, spool_id: UUID) -> tuple[FilamentReservation, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (item for item in self._items.values() if item.spool_id == spool_id),
                    key=lambda item: (item.created_at, str(item.queue_id), item.material_index),
                )
            )

    def list(self) -> tuple[FilamentReservation, ...]:
        with self._lock:
            return tuple(
                sorted(
                    self._items.values(),
                    key=lambda item: (item.created_at, str(item.queue_id), item.material_index),
                )
            )
