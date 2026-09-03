# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import pytest

from foxforge.adapters.bambu import (
    BambuLanSettings,
    BambuLanTransport,
    BambuMaterialUnitKind,
    BambuNativeMaterialRoute,
    BambuNativePrintRequest,
    BambuTransportError,
    BambuTransportErrorKind,
)


class FakeBambuMqttWire:
    def __init__(self) -> None:
        self.connected = False
        self.published: list[dict[str, object]] = []
        self._messages: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()
        self.project_response = True
        self.project_publish_error: BambuTransportError | None = None

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        if not self.connected:
            return
        self.connected = False
        await self._messages.put(None)

    async def publish(self, payload: dict[str, object]) -> None:
        self.published.append(payload)
        info = payload.get("info")
        if isinstance(info, dict) and info.get("command") == "get_version":
            await self.push(
                {
                    "info": {
                        "command": "get_version",
                        "sequence_id": info.get("sequence_id"),
                        "module": [{"name": "n3f/0"}],
                    }
                }
            )
            return

        pushing = payload.get("pushing")
        if isinstance(pushing, dict) and pushing.get("command") == "pushall":
            await self.push(_idle_status())
            return

        print_data = payload.get("print")
        if not isinstance(print_data, dict) or print_data.get("command") != "project_file":
            return
        if self.project_publish_error is not None:
            raise self.project_publish_error
        if self.project_response:
            await self.push(
                {
                    "print": {
                        "command": "project_file",
                        "sequence_id": print_data.get("sequence_id"),
                        "result": "success",
                        "subtask_id": "job-42",
                    }
                }
            )

    def messages(self) -> AsyncIterator[dict[str, object]]:
        return self._iterate_messages()

    async def push(self, payload: dict[str, object]) -> None:
        await self._messages.put(payload)

    async def _iterate_messages(self) -> AsyncIterator[dict[str, object]]:
        while True:
            item = await self._messages.get()
            if item is None:
                return
            yield item


class FakeBambuFtpsWire:
    def __init__(self, on_upload: Callable[[], Awaitable[None]] | None = None) -> None:
        self.uploads: list[tuple[Path, str]] = []
        self._on_upload = on_upload

    async def upload(self, local_path: Path, remote_filename: str) -> None:
        self.uploads.append((local_path, remote_filename))
        if self._on_upload is not None:
            await self._on_upload()


def _settings() -> BambuLanSettings:
    return BambuLanSettings(
        host="192.0.2.10",
        serial_number="01P00FOXFORGE",
        access_code="12345678",
        connect_timeout_seconds=0.2,
        command_timeout_seconds=0.05,
    )


def _request(tmp_path: Path) -> BambuNativePrintRequest:
    path = tmp_path / "foxforge.3mf"
    path.write_bytes(b"PK\x03\x04foxforge-bambu")
    return BambuNativePrintRequest(
        local_path=path,
        filename=path.name,
        plate_number=2,
        material_routes=(
            BambuNativeMaterialRoute(material_index=0, ams_id=0, tray_id=1),
            BambuNativeMaterialRoute(material_index=1, ams_id=0, tray_id=3),
        ),
        requested_name="FoxForge safety test",
    )


def _idle_status() -> dict[str, object]:
    return {
        "print": {
            "command": "push_status",
            "gcode_state": "IDLE",
            "mc_percent": 0,
            "ams": {
                "tray_now": "1",
                "tray_exist_bits": "A",
                "ams": [
                    {
                        "id": "0",
                        "tray": [
                            {"id": "1", "tray_type": "PETG", "tray_color": "FF6600FF", "remain": 80},
                            {"id": "3", "tray_type": "PLA", "tray_color": "FFFFFFFF", "remain": 55},
                        ],
                    }
                ],
            },
        }
    }


async def _settle() -> None:
    await asyncio.sleep(0)
    await asyncio.sleep(0)


def test_connect_merges_version_and_sticky_incremental_status() -> None:
    async def scenario() -> None:
        mqtt = FakeBambuMqttWire()
        transport = BambuLanTransport(_settings(), mqtt_wire=mqtt, ftps_wire=FakeBambuFtpsWire())
        try:
            await transport.connect()
            snapshot = transport.snapshot()
            assert snapshot.connected is True
            assert snapshot.gcode_state == "IDLE"
            assert len(snapshot.material_units) == 1
            assert snapshot.material_units[0].kind == BambuMaterialUnitKind.AMS_2_PRO
            assert [tray.tray_id for tray in snapshot.material_units[0].trays] == [1, 3]

            await mqtt.push({"print": {"command": "push_status", "mc_percent": 37}})
            await _settle()
            updated = transport.snapshot()
            assert updated.progress_percent == 37
            assert len(updated.material_units) == 1
            assert updated.material_units[0].kind == BambuMaterialUnitKind.AMS_2_PRO
            assert [tray.tray_id for tray in updated.material_units[0].trays] == [1, 3]
        finally:
            await transport.disconnect()

    asyncio.run(scenario())


def test_submit_uploads_before_project_file_and_maps_plate_and_ams(tmp_path: Path) -> None:
    async def scenario() -> None:
        mqtt = FakeBambuMqttWire()
        ftps = FakeBambuFtpsWire()
        transport = BambuLanTransport(_settings(), mqtt_wire=mqtt, ftps_wire=ftps)
        try:
            await transport.connect()
            receipt = await transport.submit_print(_request(tmp_path))

            assert ftps.uploads == [(tmp_path / "foxforge.3mf", "foxforge.3mf")]
            project = [
                payload["print"]
                for payload in mqtt.published
                if isinstance(payload.get("print"), dict) and payload["print"].get("command") == "project_file"
            ]
            assert len(project) == 1
            command = project[0]
            assert command["param"] == "Metadata/plate_2.gcode"
            assert command["file"] == "foxforge.3mf"
            assert command["url"] == "ftp:///foxforge.3mf"
            assert command["use_ams"] is True
            assert command["ams_mapping"] == [1, 3]
            assert command["ams_mapping2"] == [
                {"ams_id": 0, "slot_id": 1},
                {"ams_id": 0, "slot_id": 3},
            ]
            assert receipt.vendor_job_id == "job-42"
        finally:
            await transport.disconnect()

    asyncio.run(scenario())


def test_busy_printer_is_rejected_before_upload(tmp_path: Path) -> None:
    async def scenario() -> None:
        mqtt = FakeBambuMqttWire()
        ftps = FakeBambuFtpsWire()
        transport = BambuLanTransport(_settings(), mqtt_wire=mqtt, ftps_wire=ftps)
        try:
            await transport.connect()
            await mqtt.push({"print": {"command": "push_status", "gcode_state": "RUNNING"}})
            await _settle()

            with pytest.raises(BambuTransportError) as caught:
                await transport.submit_print(_request(tmp_path))
            assert caught.value.kind == BambuTransportErrorKind.BUSY
            assert ftps.uploads == []
        finally:
            await transport.disconnect()

    asyncio.run(scenario())


def test_second_busy_guard_prevents_start_after_upload_race(tmp_path: Path) -> None:
    async def scenario() -> None:
        mqtt = FakeBambuMqttWire()

        async def become_busy() -> None:
            await mqtt.push({"print": {"command": "push_status", "gcode_state": "RUNNING"}})
            await _settle()

        ftps = FakeBambuFtpsWire(become_busy)
        transport = BambuLanTransport(_settings(), mqtt_wire=mqtt, ftps_wire=ftps)
        try:
            await transport.connect()
            with pytest.raises(BambuTransportError) as caught:
                await transport.submit_print(_request(tmp_path))
            assert caught.value.kind == BambuTransportErrorKind.BUSY
            assert len(ftps.uploads) == 1
            assert not any(
                isinstance(payload.get("print"), dict) and payload["print"].get("command") == "project_file"
                for payload in mqtt.published
            )
        finally:
            await transport.disconnect()

    asyncio.run(scenario())


def test_ambiguous_project_publish_becomes_indeterminate(tmp_path: Path) -> None:
    async def scenario() -> None:
        mqtt = FakeBambuMqttWire()
        mqtt.project_publish_error = BambuTransportError(BambuTransportErrorKind.TIMEOUT, "qos1 ack timeout")
        transport = BambuLanTransport(_settings(), mqtt_wire=mqtt, ftps_wire=FakeBambuFtpsWire())
        try:
            await transport.connect()
            with pytest.raises(BambuTransportError) as caught:
                await transport.submit_print(_request(tmp_path))
            assert caught.value.kind == BambuTransportErrorKind.INDETERMINATE
        finally:
            await transport.disconnect()

    asyncio.run(scenario())


def test_missing_project_response_becomes_indeterminate(tmp_path: Path) -> None:
    async def scenario() -> None:
        mqtt = FakeBambuMqttWire()
        mqtt.project_response = False
        transport = BambuLanTransport(_settings(), mqtt_wire=mqtt, ftps_wire=FakeBambuFtpsWire())
        try:
            await transport.connect()
            with pytest.raises(BambuTransportError) as caught:
                await transport.submit_print(_request(tmp_path))
            assert caught.value.kind == BambuTransportErrorKind.INDETERMINATE
        finally:
            await transport.disconnect()

    asyncio.run(scenario())
