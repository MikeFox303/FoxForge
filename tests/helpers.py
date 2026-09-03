# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
from pathlib import Path

from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat


def make_artifact(
    path: Path,
    *,
    artifact_format: PrintArtifactFormat = PrintArtifactFormat.GCODE,
    payload: bytes = b"G28\nG1 X10 Y10\n",
) -> LocalPrintArtifact:
    path.write_bytes(payload)
    return LocalPrintArtifact(
        artifact_id="artifact-1",
        path=path.resolve(),
        filename=path.name,
        format=artifact_format,
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
