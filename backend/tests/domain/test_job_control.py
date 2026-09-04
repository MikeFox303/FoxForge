# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from dataclasses import replace
from uuid import uuid4

from foxforge.domain.printers import (
    ActiveJobSnapshot,
    ConnectionState,
    JobState,
    OperationalState,
    PrinterSnapshot,
    utc_now,
)
from foxforge.domain.printers.capabilities import (
    JOB_CONTROL_CAPABILITY_ID,
    JOB_CONTROL_MAJOR_VERSION,
    JobControlAction,
    JobControlBlockerCode,
    JobControlDescriptor,
    JobControlRequest,
    assess_job_control,
)


def _descriptor() -> JobControlDescriptor:
    return JobControlDescriptor(
        capability_id=JOB_CONTROL_CAPABILITY_ID,
        major_version=JOB_CONTROL_MAJOR_VERSION,
        supported_actions=frozenset(JobControlAction),
    )


def _snapshot(state: JobState = JobState.PRINTING) -> PrinterSnapshot:
    return PrinterSnapshot(
        printer_id="printer-1",
        connection=ConnectionState.CONNECTED,
        operational_state=OperationalState.PRINTING,
        active_job=ActiveJobSnapshot(
            vendor_job_id="vendor-job-1",
            name="job.3mf",
            state=state,
            progress=0.4,
            elapsed_seconds=60,
            remaining_seconds=90,
            current_layer=10,
            total_layers=25,
        ),
        observed_at=utc_now(),
        stale=False,
    )


def _request(action: JobControlAction, vendor_job_id: str = "vendor-job-1") -> JobControlRequest:
    return JobControlRequest(
        control_id=uuid4(),
        action=action,
        expected_vendor_job_id=vendor_job_id,
    )


def test_pause_requires_current_printing_job_identity() -> None:
    assessment = assess_job_control(_snapshot(), _descriptor(), _request(JobControlAction.PAUSE))
    assert assessment.eligible
    assert assessment.blockers == ()


def test_resume_is_allowed_only_from_paused_state() -> None:
    rejected = assess_job_control(_snapshot(), _descriptor(), _request(JobControlAction.RESUME))
    assert not rejected.eligible
    assert JobControlBlockerCode.INVALID_STATE in {item.code for item in rejected.blockers}

    paused = replace(
        _snapshot(JobState.PAUSED),
        operational_state=OperationalState.PAUSED,
        observed_at=utc_now(),
    )
    accepted = assess_job_control(paused, _descriptor(), _request(JobControlAction.RESUME))
    assert accepted.eligible


def test_control_blocks_stale_or_mismatched_job() -> None:
    stale = replace(_snapshot(), stale=True)
    stale_assessment = assess_job_control(stale, _descriptor(), _request(JobControlAction.CANCEL))
    assert JobControlBlockerCode.STALE in {item.code for item in stale_assessment.blockers}

    mismatch = assess_job_control(_snapshot(), _descriptor(), _request(JobControlAction.CANCEL, "other-job"))
    assert JobControlBlockerCode.JOB_MISMATCH in {item.code for item in mismatch.blockers}


def test_control_blocks_job_without_vendor_identity() -> None:
    snapshot = replace(
        _snapshot(),
        active_job=replace(_snapshot().active_job, vendor_job_id=None),
        observed_at=utc_now(),
    )
    assessment = assess_job_control(snapshot, _descriptor(), _request(JobControlAction.CANCEL))
    assert JobControlBlockerCode.JOB_IDENTITY_UNAVAILABLE in {item.code for item in assessment.blockers}
