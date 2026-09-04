# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

import asyncio
import hashlib
import os
import time

import pytest

from foxforge.application.artifacts import ArtifactHashMismatchError, ArtifactStorageFullError, ArtifactTooLargeError
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


def test_total_quota_blocks_new_content_but_not_content_addressed_replay(tmp_path) -> None:
    async def scenario() -> None:
        root = tmp_path / "artifacts"
        store = FilesystemArtifactStore(root, total_quota_bytes=15)
        first_payload = b"0123456789"
        first_hash = hashlib.sha256(first_payload).hexdigest()
        second_payload = b"abcdefghij"
        second_hash = hashlib.sha256(second_payload).hexdigest()

        first = await store.stage(
            filename="first.gcode",
            format=PrintArtifactFormat.GCODE,
            expected_sha256=first_hash,
            chunks=_chunks(first_payload),
            max_size_bytes=100,
        )
        assert first.replayed is False

        with pytest.raises(ArtifactStorageFullError, match="total quota"):
            await store.stage(
                filename="second.gcode",
                format=PrintArtifactFormat.GCODE,
                expected_sha256=second_hash,
                chunks=_chunks(second_payload),
                max_size_bytes=100,
            )

        replay = await store.stage(
            filename="same.gcode",
            format=PrintArtifactFormat.GCODE,
            expected_sha256=first_hash,
            chunks=_chunks(first_payload),
            max_size_bytes=100,
        )
        assert replay.replayed is True
        assert store.stats().artifact_count == 1
        assert store.stats().used_bytes == len(first_payload)
        assert list((root / ".tmp").iterdir()) == []

    asyncio.run(scenario())


def test_cleanup_removes_only_old_unreferenced_artifacts_and_stale_temp_dirs(tmp_path) -> None:
    async def scenario() -> None:
        root = tmp_path / "artifacts"
        store = FilesystemArtifactStore(root)
        referenced_payload = b"G28\n"
        orphan_payload = b"G1 X10\n"
        referenced_hash = hashlib.sha256(referenced_payload).hexdigest()
        orphan_hash = hashlib.sha256(orphan_payload).hexdigest()

        await store.stage(
            filename="referenced.gcode",
            format=PrintArtifactFormat.GCODE,
            expected_sha256=referenced_hash,
            chunks=_chunks(referenced_payload),
            max_size_bytes=100,
        )
        await store.stage(
            filename="orphan.gcode",
            format=PrintArtifactFormat.GCODE,
            expected_sha256=orphan_hash,
            chunks=_chunks(orphan_payload),
            max_size_bytes=100,
        )

        old = time.time() - 7200
        os.utime(root / referenced_hash, (old, old))
        os.utime(root / orphan_hash, (old, old))
        stale_temp = root / ".tmp" / "stale-upload"
        stale_temp.mkdir()
        os.utime(stale_temp, (old, old))

        result = store.cleanup(
            referenced_artifact_ids={referenced_hash},
            orphan_retention_seconds=3600,
            temp_retention_seconds=3600,
        )

        assert result.removed_artifact_ids == (orphan_hash,)
        assert result.removed_bytes == len(orphan_payload)
        assert result.removed_temp_directories == 1
        assert store.get(referenced_hash).sha256 == referenced_hash
        assert not (root / orphan_hash).exists()
        assert not stale_temp.exists()

    asyncio.run(scenario())
