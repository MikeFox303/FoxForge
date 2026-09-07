# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Vendor-independent filament reservation, settlement, and queue policy core.

Candidate 6 R3 keeps provider enablement outside this package. Runtime wiring
remains explicit and evidence-gated while the queue policy itself stays common.
"""

from .models import FilamentReservation, FilamentReservationState, MaterialEstimate
from .queue_policy import FilamentAccountingQueuePolicy
from .service import (
    FilamentAccountingError,
    FilamentAccountingService,
    FilamentAssignmentRequiredError,
    FilamentCapacityError,
    FilamentPlanConflictError,
    FilamentReconciliationConflictError,
    FilamentReconciliationRequiredError,
    FilamentReservationNotFoundError,
    FilamentSettlementConflictError,
    FilamentSettlementError,
)
from .store import (
    FilamentAccountingStore,
    FilamentAccountingStoreConflictError,
    FilamentAccountingStoreMissingError,
    InMemoryFilamentAccountingStore,
)

__all__ = [
    "FilamentAccountingError",
    "FilamentAccountingQueuePolicy",
    "FilamentAccountingService",
    "FilamentAccountingStore",
    "FilamentAccountingStoreConflictError",
    "FilamentAccountingStoreMissingError",
    "FilamentAssignmentRequiredError",
    "FilamentCapacityError",
    "FilamentPlanConflictError",
    "FilamentReconciliationConflictError",
    "FilamentReconciliationRequiredError",
    "FilamentReservation",
    "FilamentReservationNotFoundError",
    "FilamentReservationState",
    "FilamentSettlementConflictError",
    "FilamentSettlementError",
    "InMemoryFilamentAccountingStore",
    "MaterialEstimate",
]
