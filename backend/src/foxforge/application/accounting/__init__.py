# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Vendor-independent filament reservation and settlement application core.

Candidate 6 R2 adds durable planning/settlement semantics while printer dispatch
integration remains a later R3 slice against the current QueueService routing
pipeline.
"""

from .models import FilamentReservation, FilamentReservationState, MaterialEstimate
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
