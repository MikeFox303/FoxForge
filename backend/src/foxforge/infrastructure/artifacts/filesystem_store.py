# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import time
from collections.abc import AsyncIterable, Collection
from pathlib import Path
from uuid import uuid4

from foxforge.application.artifacts import (
    ArtifactCleanupResult,
    ArtifactFormatConflictError,
    ArtifactHashMismatchError,
    ArtifactNotFoundError,
    ArtifactStageResult,
    ArtifactStorageFullError,
    ArtifactStorageStats,
    ArtifactTooLargeError,
)
from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat

_METADATA_SCHEMA_VERSION = 1


class FilesystemArtifactStore:
    """Restart-safe content-addressed storage with bounded lifecycle management."""

    def __init__(
        self,
        root: Path | str,
        *,
        total_quota_bytes: int | None = None,
        min_free_bytes: int = 0,
    ) -> None:
        if total_quota_bytes is not None and total_quota_bytes <= 0:
            raise ValueError("total_quota_bytes must be positive when configured")
        if min_free_bytes < 0:
            raise ValueError("min_free_bytes must be non-negative")
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / ".tmp").mkdir(parents=True, exist_ok=True)
        self._total_quota_bytes = total_quota_bytes
        self._min_free_bytes = min_free_bytes
        self._stage_lock = asyncio.Lock()

    @property
    def root(self) -> Path:
        return self._root

    async def stage(
        self,
        *,
        filename: str,
        format: PrintArtifactFormat,
        expected_sha256: str,
        chunks: AsyncIterable[bytes],
        max_size_bytes: int,
    ) -> ArtifactStageResult:
        if max_size_bytes <= 0:
            raise ValueError("max_size_bytes must be positive")
        expected = _sha256(expected_sha256)

        async with self._stage_lock:
            existing = self._root / expected
            if existing.is_dir():
                artifact = self.get(expected)
                if artifact.format != format:
                    raise ArtifactFormatConflictError(expected)
                return ArtifactStageResult(artifact=artifact, replayed=True)

            temp_dir = self._root / ".tmp" / str(uuid4())
            temp_dir.mkdir(mode=0o700)
            payload_path = temp_dir / "payload"
            size_bytes = 0
            digest = hashlib.sha256()
            try:
                with payload_path.open("xb") as stream:
                    async for chunk in chunks:
                        if not isinstance(chunk, bytes):
                            chunk = bytes(chunk)
                        if not chunk:
                            continue
                        size_bytes += len(chunk)
                        if size_bytes > max_size_bytes:
                            raise ArtifactTooLargeError(max_size_bytes)
                        digest.update(chunk)
                        stream.write(chunk)
                    stream.flush()

                actual = digest.hexdigest()
                if actual != expected:
                    raise ArtifactHashMismatchError(expected, actual)

                self._require_capacity(size_bytes)
                metadata = {
                    "schemaVersion": _METADATA_SCHEMA_VERSION,
                    "artifactId": expected,
                    "filename": filename,
                    "format": format.value,
                    "sizeBytes": size_bytes,
                    "sha256": expected,
                }
                (temp_dir / "metadata.json").write_text(
                    json.dumps(metadata, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8",
                )

                try:
                    temp_dir.rename(existing)
                except FileExistsError as error:
                    artifact = self.get(expected)
                    if artifact.format != format:
                        raise ArtifactFormatConflictError(expected) from error
                    return ArtifactStageResult(artifact=artifact, replayed=True)

                return ArtifactStageResult(artifact=self.get(expected), replayed=False)
            finally:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)

    def get(self, artifact_id: str) -> LocalPrintArtifact:
        normalized = _sha256(artifact_id)
        artifact_dir = self._root / normalized
        metadata_path = artifact_dir / "metadata.json"
        payload_path = artifact_dir / "payload"
        if not metadata_path.is_file() or not payload_path.is_file():
            raise ArtifactNotFoundError(normalized)

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ArtifactNotFoundError(normalized) from error
        if not isinstance(metadata, dict) or metadata.get("schemaVersion") != _METADATA_SCHEMA_VERSION:
            raise ArtifactNotFoundError(normalized)
        if metadata.get("artifactId") != normalized or metadata.get("sha256") != normalized:
            raise ArtifactNotFoundError(normalized)

        filename = metadata.get("filename")
        raw_format = metadata.get("format")
        size_bytes = metadata.get("sizeBytes")
        if not isinstance(filename, str) or not filename:
            raise ArtifactNotFoundError(normalized)
        if not isinstance(size_bytes, int) or size_bytes < 0:
            raise ArtifactNotFoundError(normalized)
        try:
            artifact_format = PrintArtifactFormat(str(raw_format))
        except ValueError as error:
            raise ArtifactNotFoundError(normalized) from error
        if payload_path.stat().st_size != size_bytes:
            raise ArtifactNotFoundError(normalized)

        return LocalPrintArtifact(
            artifact_id=normalized,
            path=payload_path.resolve(),
            filename=filename,
            format=artifact_format,
            size_bytes=size_bytes,
            sha256=normalized,
        )

    def stats(self) -> ArtifactStorageStats:
        artifacts = tuple(self._artifact_directories())
        used_bytes = sum(_payload_size(path) for path in artifacts)
        free_bytes = shutil.disk_usage(self._root).free
        return ArtifactStorageStats(
            artifact_count=len(artifacts),
            used_bytes=used_bytes,
            total_quota_bytes=self._total_quota_bytes,
            free_bytes=free_bytes,
            min_free_bytes=self._min_free_bytes,
        )

    def cleanup(
        self,
        *,
        referenced_artifact_ids: Collection[str],
        orphan_retention_seconds: float,
        temp_retention_seconds: float,
    ) -> ArtifactCleanupResult:
        if orphan_retention_seconds < 0 or temp_retention_seconds < 0:
            raise ValueError("artifact retention values must be non-negative")
        referenced = {_sha256(artifact_id) for artifact_id in referenced_artifact_ids}
        now = time.time()
        removed_ids: list[str] = []
        removed_bytes = 0

        for artifact_dir in self._artifact_directories():
            if artifact_dir.name in referenced:
                continue
            if now - artifact_dir.stat().st_mtime < orphan_retention_seconds:
                continue
            removed_bytes += _payload_size(artifact_dir)
            removed_ids.append(artifact_dir.name)
            shutil.rmtree(artifact_dir)

        removed_temp = 0
        temp_root = self._root / ".tmp"
        for temp_dir in tuple(temp_root.iterdir()):
            if not temp_dir.is_dir():
                continue
            if now - temp_dir.stat().st_mtime < temp_retention_seconds:
                continue
            shutil.rmtree(temp_dir)
            removed_temp += 1

        return ArtifactCleanupResult(
            removed_artifact_ids=tuple(sorted(removed_ids)),
            removed_bytes=removed_bytes,
            removed_temp_directories=removed_temp,
        )

    def _require_capacity(self, incoming_bytes: int) -> None:
        stats = self.stats()
        if self._total_quota_bytes is not None and stats.used_bytes + incoming_bytes > self._total_quota_bytes:
            raise ArtifactStorageFullError("artifact storage total quota would be exceeded")
        if stats.free_bytes < self._min_free_bytes:
            raise ArtifactStorageFullError("artifact storage free-space reserve would be violated")

    def _artifact_directories(self):
        for candidate in self._root.iterdir():
            if candidate.name == ".tmp" or not candidate.is_dir():
                continue
            try:
                _sha256(candidate.name)
            except ValueError:
                continue
            yield candidate


def _payload_size(artifact_dir: Path) -> int:
    payload = artifact_dir / "payload"
    return payload.stat().st_size if payload.is_file() else 0


def _sha256(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError("artifact SHA-256 must contain 64 hexadecimal characters")
    return normalized
