# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from datetime import datetime

import pytest

from foxforge.domain.printers import ActiveJobSnapshot, JobState, PrinterSnapshot
from foxforge.domain.printers.capabilities import DetectedMaterial


def test_common_domain_rejects_naive_timestamps(printer_identity) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        PrinterSnapshot(
            printer_id=printer_identity.printer_id,
            connection="disconnected",  # type: ignore[arg-type]
            operational_state="offline",  # type: ignore[arg-type]
            active_job=None,
            observed_at=datetime(2026, 9, 3),
            stale=False,
        )


def test_common_domain_rejects_sentinel_progress() -> None:
    with pytest.raises(ValueError, match="progress"):
        ActiveJobSnapshot(
            vendor_job_id=None,
            name=None,
            state=JobState.PRINTING,
            progress=-1.0,
            elapsed_seconds=None,
            remaining_seconds=None,
            current_layer=None,
            total_layers=None,
        )


def test_detected_material_rejects_invalid_remaining_fraction() -> None:
    with pytest.raises(ValueError, match="remaining_fraction"):
        DetectedMaterial(None, None, None, None, None, 1.1)
