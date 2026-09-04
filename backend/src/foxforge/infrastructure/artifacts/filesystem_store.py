# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import AsyncIterable
from pathlib import Path
from uuid import uuid4

from foxforge.application.artifacts import (
    ArtifactFormatConflictError,
    ArtifactHashMismatchError,
    ArtifactNotFoundError,
    ArtifactStageResult,
    ArtifactTooLargeError,
)
from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat

_METADATA_SCHEMA_VERSION = 1


class FilesystemArtifactStore:
    """Restart-safe content-addressed storage for uploaded print artifacts."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / ".tmp").mkdir(parents=True, exist_ok=True)

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


def _sha256(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError("artifact SHA-256 must contain 64 hexadecimal characters")
    return normalized
