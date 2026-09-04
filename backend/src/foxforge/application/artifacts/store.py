# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import AsyncIterable, Collection
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


class ArtifactStorageFullError(RuntimeError):
    def __init__(self, message: str = "artifact storage quota or free-space reserve would be exceeded") -> None:
        super().__init__(message)


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


@dataclass(frozen=True, slots=True)
class ArtifactStorageStats:
    artifact_count: int
    used_bytes: int
    total_quota_bytes: int | None
    free_bytes: int
    min_free_bytes: int


@dataclass(frozen=True, slots=True)
class ArtifactCleanupResult:
    removed_artifact_ids: tuple[str, ...]
    removed_bytes: int
    removed_temp_directories: int


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

    def stats(self) -> ArtifactStorageStats: ...

    def cleanup(
        self,
        *,
        referenced_artifact_ids: Collection[str],
        orphan_retention_seconds: float,
        temp_retention_seconds: float,
    ) -> ArtifactCleanupResult: ...
