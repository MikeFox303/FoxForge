# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from foxforge.adapters.bambu import (
    BambuLanSettings,
    BambuLanTransport,
    BambuNativePrintRequest,
    BambuProjectStorageKind,
    BambuStoredProject,
    BambuTransportError,
    FtpsBambuProjectStorage,
)


class _FakeFtpsWire:
    def __init__(self) -> None:
        self.uploads: list[tuple[Path, str]] = []

    async def upload(self, local_path: Path, remote_filename: str) -> None:
        self.uploads.append((local_path, remote_filename))


class _FakeProjectStorage:
    def __init__(self, project: BambuStoredProject) -> None:
        self.project = project
        self.uploads: list[tuple[Path, str]] = []

    async def upload(self, local_path: Path, remote_filename: str) -> BambuStoredProject:
        self.uploads.append((local_path, remote_filename))
        return self.project


class _FakeMqttWire:
    def __init__(self) -> None:
        self.published: list[dict[str, object]] = []
        self._messages: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        await self._messages.put(None)

    async def publish(self, payload: dict[str, object]) -> None:
        self.published.append(payload)
        pushing = payload.get("pushing")
        if isinstance(pushing, dict) and pushing.get("command") == "pushall":
            await self._messages.put(
                {
                    "print": {
                        "command": "push_status",
                        "gcode_state": "IDLE",
                    }
                }
            )
            return
        print_data = payload.get("print")
        if isinstance(print_data, dict) and print_data.get("command") == "project_file":
            await self._messages.put(
                {
                    "print": {
                        "command": "project_file",
                        "sequence_id": print_data.get("sequence_id"),
                        "result": "success",
                        "subtask_id": "storage-test-job",
                    }
                }
            )

    def messages(self) -> AsyncIterator[dict[str, object]]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[dict[str, object]]:
        while True:
            payload = await self._messages.get()
            if payload is None:
                return
            yield payload


def _settings() -> BambuLanSettings:
    return BambuLanSettings(
        host="192.0.2.40",
        serial_number="01P00STORAGE",
        access_code="12345678",
        connect_timeout_seconds=0.2,
        command_timeout_seconds=0.2,
    )


def _request(tmp_path: Path) -> BambuNativePrintRequest:
    path = tmp_path / "storage.3mf"
    path.write_bytes(b"PK\x03\x04storage-seam")
    return BambuNativePrintRequest(
        local_path=path,
        filename=path.name,
        plate_number=1,
        material_routes=(),
        requested_name="Storage seam",
    )


def test_ftps_storage_returns_ftp_project_reference(tmp_path: Path) -> None:
    async def scenario() -> None:
        source = tmp_path / "job.3mf"
        source.write_bytes(b"PK\x03\x04ftps-storage")
        wire = _FakeFtpsWire()
        storage = FtpsBambuProjectStorage(wire)

        project = await storage.upload(source, source.name)

        assert wire.uploads == [(source, "job.3mf")]
        assert project == BambuStoredProject(
            remote_filename="job.3mf",
            project_url="ftp:///job.3mf",
            storage_kind=BambuProjectStorageKind.FTPS,
        )

    asyncio.run(scenario())


def test_stored_project_validates_storage_specific_urls() -> None:
    emmc = BambuStoredProject(
        remote_filename="job.3mf",
        project_url="brtc://emmc/job.3mf",
        storage_kind=BambuProjectStorageKind.INTERNAL_EMMC,
    )
    assert emmc.project_url == "brtc://emmc/job.3mf"

    with pytest.raises(ValueError, match="brtc://emmc"):
        BambuStoredProject(
            remote_filename="job.3mf",
            project_url="ftp:///job.3mf",
            storage_kind=BambuProjectStorageKind.INTERNAL_EMMC,
        )

    with pytest.raises(ValueError, match="remote_filename"):
        BambuStoredProject(
            remote_filename="job.3mf",
            project_url="brtc://emmc/other.3mf",
            storage_kind=BambuProjectStorageKind.INTERNAL_EMMC,
        )


def test_ftps_storage_rejects_path_like_remote_filename(tmp_path: Path) -> None:
    source = tmp_path / "job.3mf"
    source.write_bytes(b"PK\x03\x04invalid-name")

    with pytest.raises(BambuTransportError):
        asyncio.run(FtpsBambuProjectStorage(_FakeFtpsWire()).upload(source, "../job.3mf"))


def test_transport_uses_storage_owned_brtc_url_without_x2d_import(tmp_path: Path) -> None:
    async def scenario() -> None:
        mqtt = _FakeMqttWire()
        project = BambuStoredProject(
            remote_filename="storage.3mf",
            project_url="brtc://emmc/storage.3mf",
            storage_kind=BambuProjectStorageKind.INTERNAL_EMMC,
        )
        storage = _FakeProjectStorage(project)
        transport = BambuLanTransport(_settings(), mqtt_wire=mqtt, project_storage=storage)
        request = _request(tmp_path)
        try:
            await transport.connect()
            result = await transport.submit_print(request)

            assert storage.uploads == [(request.local_path, "storage.3mf")]
            project_commands = [
                payload["print"]
                for payload in mqtt.published
                if isinstance(payload.get("print"), dict) and payload["print"].get("command") == "project_file"
            ]
            assert len(project_commands) == 1
            assert project_commands[0]["file"] == "storage.3mf"
            assert project_commands[0]["url"] == "brtc://emmc/storage.3mf"
            assert result.vendor_job_id == "storage-test-job"
        finally:
            await transport.disconnect()

    asyncio.run(scenario())


def test_transport_rejects_ambiguous_storage_injection() -> None:
    project = BambuStoredProject(
        remote_filename="job.3mf",
        project_url="brtc://emmc/job.3mf",
        storage_kind=BambuProjectStorageKind.INTERNAL_EMMC,
    )

    with pytest.raises(ValueError, match="either ftps_wire or project_storage"):
        BambuLanTransport(
            _settings(),
            ftps_wire=_FakeFtpsWire(),
            project_storage=_FakeProjectStorage(project),
        )
