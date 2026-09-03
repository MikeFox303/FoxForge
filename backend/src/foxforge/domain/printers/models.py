# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

PrinterId = str
MaterialUnitId = str
MaterialSlotId = str
VendorJobId = str
FaultSeverity = Literal["info", "warning", "error", "critical"]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def normalize_utc(value: datetime, *, field_name: str = "timestamp") -> datetime:
    """Validate an aware instant and normalize it to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def validate_fraction(value: float | None, *, field_name: str) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")


def validate_nonnegative(value: int | None, *, field_name: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must be non-negative")


class ConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"


class OperationalState(StrEnum):
    OFFLINE = "offline"
    IDLE = "idle"
    PREPARING = "preparing"
    PRINTING = "printing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLING = "cancelling"
    UNKNOWN = "unknown"


class JobState(StrEnum):
    QUEUED = "queued"
    TRANSFERRING = "transferring"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    PRINTING = "printing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PrinterIdentity:
    printer_id: PrinterId
    display_name: str
    vendor: str
    model: str | None
    serial_number: str | None
    adapter_kind: str

    def __post_init__(self) -> None:
        for name in ("printer_id", "display_name", "vendor", "adapter_kind"):
            if not getattr(self, name):
                raise ValueError(f"{name} must not be empty")


@dataclass(frozen=True, slots=True)
class ActiveJobSnapshot:
    vendor_job_id: VendorJobId | None
    name: str | None
    state: JobState
    progress: float | None
    elapsed_seconds: int | None
    remaining_seconds: int | None
    current_layer: int | None
    total_layers: int | None

    def __post_init__(self) -> None:
        validate_fraction(self.progress, field_name="progress")
        validate_nonnegative(self.elapsed_seconds, field_name="elapsed_seconds")
        validate_nonnegative(self.remaining_seconds, field_name="remaining_seconds")
        validate_nonnegative(self.current_layer, field_name="current_layer")
        validate_nonnegative(self.total_layers, field_name="total_layers")
        if self.current_layer is not None and self.total_layers is not None and self.current_layer > self.total_layers:
            raise ValueError("current_layer must not exceed total_layers")


@dataclass(frozen=True, slots=True)
class PrinterFaultSummary:
    code: str
    severity: FaultSeverity
    message: str | None

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("code must not be empty")
        if self.severity not in {"info", "warning", "error", "critical"}:
            raise ValueError("severity is invalid")


@dataclass(frozen=True, slots=True)
class PrinterSnapshot:
    printer_id: PrinterId
    connection: ConnectionState
    operational_state: OperationalState
    active_job: ActiveJobSnapshot | None
    observed_at: datetime
    stale: bool
    fault_summary: tuple[PrinterFaultSummary, ...] = ()

    def __post_init__(self) -> None:
        if not self.printer_id:
            raise ValueError("printer_id must not be empty")
        object.__setattr__(self, "observed_at", normalize_utc(self.observed_at, field_name="observed_at"))


@dataclass(frozen=True, slots=True)
class CapabilityDescriptor:
    capability_id: str
    major_version: int

    def __post_init__(self) -> None:
        if not self.capability_id:
            raise ValueError("capability_id must not be empty")
        if self.major_version <= 0:
            raise ValueError("major_version must be positive")
