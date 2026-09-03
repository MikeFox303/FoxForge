# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import UUID

from ..models import CapabilityDescriptor, MaterialSlotId, normalize_utc

PRINT_EXECUTION_CAPABILITY_ID = "foxforge.print_execution"
PRINT_EXECUTION_MAJOR_VERSION = 1


class PrintArtifactFormat(StrEnum):
    GCODE = "gcode"
    THREE_MF = "3mf"


@dataclass(frozen=True, slots=True)
class PrintExecutionDescriptor(CapabilityDescriptor):
    accepted_formats: frozenset[PrintArtifactFormat]
    supports_plate_selection: bool
    supports_material_bindings: bool

    def __post_init__(self) -> None:
        CapabilityDescriptor.__post_init__(self)
        if self.capability_id != PRINT_EXECUTION_CAPABILITY_ID or self.major_version != PRINT_EXECUTION_MAJOR_VERSION:
            raise ValueError("PrintExecutionDescriptor must describe foxforge.print_execution v1")
        if not self.accepted_formats:
            raise ValueError("accepted_formats must not be empty")


@dataclass(frozen=True, slots=True)
class LocalPrintArtifact:
    artifact_id: str
    path: Path
    filename: str
    format: PrintArtifactFormat
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("artifact_id must not be empty")
        if not self.filename:
            raise ValueError("filename must not be empty")
        if not self.path.is_absolute():
            raise ValueError("path must be absolute")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")
        normalized_hash = self.sha256.lower()
        if len(normalized_hash) != 64 or any(ch not in "0123456789abcdef" for ch in normalized_hash):
            raise ValueError("sha256 must be a 64-character hexadecimal digest")
        object.__setattr__(self, "sha256", normalized_hash)


@dataclass(frozen=True, slots=True)
class PrintArtifactSelection:
    plate_index: int | None = None

    def __post_init__(self) -> None:
        if self.plate_index is not None and self.plate_index < 0:
            raise ValueError("plate_index must be zero-based and non-negative")


@dataclass(frozen=True, slots=True)
class MaterialBinding:
    material_index: int
    slot_id: MaterialSlotId

    def __post_init__(self) -> None:
        if self.material_index < 0:
            raise ValueError("material_index must be zero-based and non-negative")
        if not self.slot_id:
            raise ValueError("slot_id must not be empty")


@dataclass(frozen=True, slots=True)
class PrintExecutionRequest:
    dispatch_id: UUID
    artifact: LocalPrintArtifact
    selection: PrintArtifactSelection | None = None
    material_bindings: tuple[MaterialBinding, ...] = ()
    requested_name: str | None = None

    def __post_init__(self) -> None:
        indices = [binding.material_index for binding in self.material_bindings]
        if len(indices) != len(set(indices)):
            raise ValueError("material_bindings must not contain duplicate material_index values")


class PrintAssessmentBlockerCode(StrEnum):
    OFFLINE = "offline"
    BUSY = "busy"
    NOT_READY = "not_ready"
    UNSUPPORTED_ARTIFACT = "unsupported_artifact"
    UNSUPPORTED_SELECTION = "unsupported_selection"
    MATERIAL_BINDING_INVALID = "material_binding_invalid"
    MATERIAL_SOURCE_UNAVAILABLE = "material_source_unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PrintAssessmentBlocker:
    code: PrintAssessmentBlockerCode
    message: str | None = None


@dataclass(frozen=True, slots=True)
class PrintExecutionAssessment:
    eligible: bool
    blockers: tuple[PrintAssessmentBlocker, ...]
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.eligible == bool(self.blockers):
            raise ValueError("eligible must be true exactly when blockers is empty")
        object.__setattr__(self, "observed_at", normalize_utc(self.observed_at, field_name="observed_at"))


@dataclass(frozen=True, slots=True)
class PrintDispatchReceipt:
    dispatch_id: UUID
    accepted_at: datetime
    vendor_job_id: str | None
    artifact_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "accepted_at", normalize_utc(self.accepted_at, field_name="accepted_at"))
        normalized_hash = self.artifact_sha256.lower()
        if len(normalized_hash) != 64 or any(ch not in "0123456789abcdef" for ch in normalized_hash):
            raise ValueError("artifact_sha256 must be a SHA-256 hexadecimal digest")
        object.__setattr__(self, "artifact_sha256", normalized_hash)


class PrintExecutionCapability(Protocol):
    @property
    def descriptor(self) -> PrintExecutionDescriptor: ...

    async def assess(self, request: PrintExecutionRequest) -> PrintExecutionAssessment: ...

    async def submit(self, request: PrintExecutionRequest) -> PrintDispatchReceipt: ...
