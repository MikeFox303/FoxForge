# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import AsyncIterable
from dataclasses import dataclass
from typing import Protocol

from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat


class ArtifactNotFoundError(KeyError):
    def __init__(self, artifact_id: str) -> None:
        self.artifact_id = artifact_id
        super().__init__(artifact_id)


class ArtifactTooLargeError(ValueError):
    def __init__(self, max_size_bytes: int) -> None:
        self.max_size_bytes = max_size_bytes
        super().__init__(f"artifact exceeds the {max_size_bytes}-byte staging limit")


class ArtifactHashMismatchError(ValueError):
    def __init__(self, expected_sha256: str, actual_sha256: str) -> None:
        self.expected_sha256 = expected_sha256
        self.actual_sha256 = actual_sha256
        super().__init__("uploaded artifact SHA-256 does not match X-FoxForge-Sha256")


class ArtifactFormatConflictError(RuntimeError):
    def __init__(self, artifact_id: str) -> None:
        self.artifact_id = artifact_id
        super().__init__(f"artifact {artifact_id} already exists with a different format")


@dataclass(frozen=True, slots=True)
class ArtifactStageResult:
    artifact: LocalPrintArtifact
    replayed: bool


class ArtifactStore(Protocol):
    async def stage(
        self,
        *,
        filename: str,
        format: PrintArtifactFormat,
        expected_sha256: str,
        chunks: AsyncIterable[bytes],
        max_size_bytes: int,
    ) -> ArtifactStageResult: ...

    def get(self, artifact_id: str) -> LocalPrintArtifact: ...
