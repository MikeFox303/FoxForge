# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

import asyncio
import hashlib

import pytest

from foxforge.application.artifacts import ArtifactHashMismatchError, ArtifactTooLargeError
from foxforge.domain.printers.capabilities import PrintArtifactFormat
from foxforge.infrastructure.artifacts import FilesystemArtifactStore


async def _chunks(payload: bytes, *, split: int = 5):
    for offset in range(0, len(payload), split):
        yield payload[offset : offset + split]


def test_filesystem_artifact_store_is_content_addressed_and_restart_safe(tmp_path) -> None:
    async def scenario() -> None:
        payload = b"; FoxForge\nG28\nG1 X10 Y10\n"
        sha256 = hashlib.sha256(payload).hexdigest()
        root = tmp_path / "artifacts"
        store = FilesystemArtifactStore(root)

        first = await store.stage(
            filename="test.gcode",
            format=PrintArtifactFormat.GCODE,
            expected_sha256=sha256,
            chunks=_chunks(payload),
            max_size_bytes=1024,
        )
        assert first.replayed is False
        assert first.artifact.artifact_id == sha256
        assert first.artifact.path.read_bytes() == payload

        replay = await store.stage(
            filename="renamed.gcode",
            format=PrintArtifactFormat.GCODE,
            expected_sha256=sha256,
            chunks=_chunks(payload),
            max_size_bytes=1024,
        )
        assert replay.replayed is True
        assert replay.artifact.path == first.artifact.path

        restored = FilesystemArtifactStore(root).get(sha256)
        assert restored == first.artifact

    asyncio.run(scenario())


def test_filesystem_artifact_store_rejects_hash_mismatch_and_size_overflow(tmp_path) -> None:
    async def scenario() -> None:
        store = FilesystemArtifactStore(tmp_path / "artifacts")
        payload = b"0123456789"
        expected = hashlib.sha256(b"different").hexdigest()

        with pytest.raises(ArtifactHashMismatchError):
            await store.stage(
                filename="bad.gcode",
                format=PrintArtifactFormat.GCODE,
                expected_sha256=expected,
                chunks=_chunks(payload),
                max_size_bytes=1024,
            )

        real_hash = hashlib.sha256(payload).hexdigest()
        with pytest.raises(ArtifactTooLargeError):
            await store.stage(
                filename="large.gcode",
                format=PrintArtifactFormat.GCODE,
                expected_sha256=real_hash,
                chunks=_chunks(payload),
                max_size_bytes=4,
            )

        assert list((tmp_path / "artifacts" / ".tmp").iterdir()) == []

    asyncio.run(scenario())
