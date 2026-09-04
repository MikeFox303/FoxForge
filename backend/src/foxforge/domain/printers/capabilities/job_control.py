# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from ..models import CapabilityDescriptor, ConnectionState, JobState, PrinterSnapshot, VendorJobId, normalize_utc

JOB_CONTROL_CAPABILITY_ID = "foxforge.job_control"
JOB_CONTROL_MAJOR_VERSION = 1


class JobControlAction(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class JobControlDescriptor(CapabilityDescriptor):
    supported_actions: frozenset[JobControlAction]
    requires_vendor_job_identity: bool = True

    def __post_init__(self) -> None:
        CapabilityDescriptor.__post_init__(self)
        if self.capability_id != JOB_CONTROL_CAPABILITY_ID or self.major_version != JOB_CONTROL_MAJOR_VERSION:
            raise ValueError("JobControlDescriptor must describe foxforge.job_control v1")
        if not self.supported_actions:
            raise ValueError("supported_actions must not be empty")


@dataclass(frozen=True, slots=True)
class JobControlRequest:
    control_id: UUID
    action: JobControlAction
    expected_vendor_job_id: VendorJobId

    def __post_init__(self) -> None:
        if not str(self.expected_vendor_job_id).strip():
            raise ValueError("expected_vendor_job_id must not be empty")


class JobControlBlockerCode(StrEnum):
    OFFLINE = "offline"
    STALE = "stale"
    NO_ACTIVE_JOB = "no_active_job"
    JOB_IDENTITY_UNAVAILABLE = "job_identity_unavailable"
    JOB_MISMATCH = "job_mismatch"
    INVALID_STATE = "invalid_state"
    UNSUPPORTED_ACTION = "unsupported_action"


@dataclass(frozen=True, slots=True)
class JobControlBlocker:
    code: JobControlBlockerCode
    message: str | None = None


@dataclass(frozen=True, slots=True)
class JobControlAssessment:
    eligible: bool
    blockers: tuple[JobControlBlocker, ...]
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.eligible == bool(self.blockers):
            raise ValueError("eligible must be true exactly when blockers is empty")
        object.__setattr__(self, "observed_at", normalize_utc(self.observed_at, field_name="observed_at"))


@dataclass(frozen=True, slots=True)
class JobControlReceipt:
    control_id: UUID
    action: JobControlAction
    accepted_at: datetime
    vendor_job_id: VendorJobId

    def __post_init__(self) -> None:
        if not str(self.vendor_job_id).strip():
            raise ValueError("vendor_job_id must not be empty")
        object.__setattr__(self, "accepted_at", normalize_utc(self.accepted_at, field_name="accepted_at"))


class JobControlCapability(Protocol):
    @property
    def descriptor(self) -> JobControlDescriptor: ...

    async def assess(self, request: JobControlRequest) -> JobControlAssessment: ...

    async def execute(self, request: JobControlRequest) -> JobControlReceipt: ...


def assess_job_control(
    snapshot: PrinterSnapshot,
    descriptor: JobControlDescriptor,
    request: JobControlRequest,
) -> JobControlAssessment:
    blockers: list[JobControlBlocker] = []

    if request.action not in descriptor.supported_actions:
        blockers.append(JobControlBlocker(JobControlBlockerCode.UNSUPPORTED_ACTION, "job control action is unsupported"))
    if snapshot.connection != ConnectionState.CONNECTED:
        blockers.append(JobControlBlocker(JobControlBlockerCode.OFFLINE, "printer is not connected"))
    if snapshot.stale:
        blockers.append(JobControlBlocker(JobControlBlockerCode.STALE, "printer snapshot is stale"))

    job = snapshot.active_job
    if job is None:
        blockers.append(JobControlBlocker(JobControlBlockerCode.NO_ACTIVE_JOB, "printer has no active job"))
    else:
        if not job.vendor_job_id:
            blockers.append(
                JobControlBlocker(
                    JobControlBlockerCode.JOB_IDENTITY_UNAVAILABLE,
                    "active job has no vendor identity; refusing to control an unverified job",
                )
            )
        elif job.vendor_job_id != request.expected_vendor_job_id:
            blockers.append(
                JobControlBlocker(
                    JobControlBlockerCode.JOB_MISMATCH,
                    "active job identity no longer matches the requested job",
                )
            )

        allowed_states = _allowed_states(request.action)
        if job.state not in allowed_states:
            blockers.append(
                JobControlBlocker(
                    JobControlBlockerCode.INVALID_STATE,
                    f"{request.action.value} is not valid while job state is {job.state.value}",
                )
            )

    return JobControlAssessment(
        eligible=not blockers,
        blockers=tuple(blockers),
        observed_at=snapshot.observed_at,
    )


def _allowed_states(action: JobControlAction) -> frozenset[JobState]:
    if action == JobControlAction.PAUSE:
        return frozenset({JobState.PRINTING})
    if action == JobControlAction.RESUME:
        return frozenset({JobState.PAUSED})
    return frozenset({JobState.PREPARING, JobState.PRINTING, JobState.PAUSED})
