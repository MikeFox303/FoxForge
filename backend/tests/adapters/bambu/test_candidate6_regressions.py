# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from foxforge.adapters.bambu import (
    BambuLanSettings,
    BambuLanTransport,
    BambuTransportError,
    BambuTransportErrorKind,
)
from foxforge.adapters.bambu.lan_codec import BambuLanCodec
from foxforge.adapters.bambu.material_topology import map_bambu_material_topology
from foxforge.adapters.bambu.native import BambuMaterialUnitKind
from foxforge.domain.printers.capabilities import MaterialRouteKind

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "bambu" / "x2d"
_SENSITIVE_KEYS = frozenset(
    {
        "access_code",
        "accessCode",
        "password",
        "token",
        "command_token",
        "serial_number",
        "serialNumber",
        "host",
        "ip",
        "cookie",
    }
)


def _load_fixture(name: str) -> object:
    return json.loads((_FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _assert_secret_safe(value: object) -> None:
    if isinstance(value, dict):
        assert _SENSITIVE_KEYS.isdisjoint(value)
        for nested in value.values():
            _assert_secret_safe(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_secret_safe(nested)


class _FixtureInitialStateMqttWire:
    def __init__(self, initial_status: dict[str, object]) -> None:
        self.connected = False
        self._initial_status = initial_status
        self._messages: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        if self.connected:
            self.connected = False
            await self._messages.put(None)

    async def publish(self, payload: dict[str, object]) -> None:
        info = payload.get("info")
        if isinstance(info, dict) and info.get("command") == "get_version":
            await self._messages.put(
                {
                    "info": {
                        "command": "get_version",
                        "sequence_id": info.get("sequence_id"),
                        "module": [{"name": "n3f/0"}],
                    }
                }
            )

        pushing = payload.get("pushing")
        if isinstance(pushing, dict) and pushing.get("command") == "pushall":
            await self._messages.put(self._initial_status)

    def messages(self) -> AsyncIterator[dict[str, object]]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[dict[str, object]]:
        while True:
            item = await self._messages.get()
            if item is None:
                return
            yield item


class _UnusedFtpsWire:
    async def upload(self, local_path: Path, remote_filename: str) -> None:
        raise AssertionError("FTPS must not run during connection preflight")


def test_candidate5_partial_x2d_status_fixture_satisfies_preflight_without_gcode_state() -> None:
    async def scenario() -> None:
        fixture = _load_fixture("candidate5_partial_initial_status.json")
        assert isinstance(fixture, dict)
        _assert_secret_safe(fixture)

        settings = BambuLanSettings(
            host="192.0.2.61",
            serial_number="CANDIDATE6TEST",
            access_code="12345678",
            connect_timeout_seconds=0.1,
        )
        mqtt = _FixtureInitialStateMqttWire(fixture)
        transport = BambuLanTransport(settings, mqtt_wire=mqtt, ftps_wire=_UnusedFtpsWire())

        await transport.connect()
        snapshot = transport.snapshot()

        assert snapshot.connected is True
        assert snapshot.gcode_state is None
        assert [unit.ams_id for unit in snapshot.material_units] == [254, 255]
        assert snapshot.material_units[0].trays[0].exists is False
        assert snapshot.material_units[1].trays[0].material_type == "PLA"

        await transport.disconnect()
        assert mqtt.connected is False

    asyncio.run(scenario())


def test_metadata_only_push_status_does_not_satisfy_initial_state_gate() -> None:
    async def scenario() -> None:
        metadata_only = {
            "print": {
                "command": "push_status",
                "sequence_id": "candidate6-metadata-only",
            }
        }
        mqtt = _FixtureInitialStateMqttWire(metadata_only)
        settings = BambuLanSettings(
            host="192.0.2.62",
            serial_number="CANDIDATE6TEST",
            access_code="12345678",
            connect_timeout_seconds=0.01,
        )
        transport = BambuLanTransport(settings, mqtt_wire=mqtt, ftps_wire=_UnusedFtpsWire())

        try:
            await transport.connect()
        except BambuTransportError as error:
            assert error.kind == BambuTransportErrorKind.TIMEOUT
            assert error.vendor_code == "initial_state_timeout"
            assert mqtt.connected is False
        else:
            raise AssertionError("metadata-only push_status must not satisfy connection preflight")

    asyncio.run(scenario())


def test_candidate5_incremental_fixture_preserves_ams_and_dual_external_sources() -> None:
    sequence = _load_fixture("candidate5_incremental_material_sequence.json")
    assert isinstance(sequence, list)
    _assert_secret_safe(sequence)

    codec = BambuLanCodec()
    state = None
    for payload in sequence:
        assert isinstance(payload, dict)
        state = codec.apply(payload)

    assert state is not None
    assert state.gcode_state is None
    assert [unit.ams_id for unit in state.material_units] == [0, 254, 255]

    ams, external_left, external_right = state.material_units
    assert ams.kind == BambuMaterialUnitKind.AMS_2_PRO
    assert [tray.material_type for tray in ams.trays] == ["PETG", "PETG", "PETG", "PETG"]
    assert external_left.label == "External Left"
    assert external_left.trays[0].exists is False
    assert external_right.label == "External Right"
    assert external_right.trays[0].material_type == "PLA"

    topology = map_bambu_material_topology("candidate6-x2d", state)
    routes = {route.source_slot_id: route for route in topology.routes}
    left = routes["bambu:unit:254:tray:0"]
    right = routes["bambu:unit:255:tray:0"]

    assert left.kind == MaterialRouteKind.FIXED
    assert left.toolhead_ids == ("bambu:toolhead:1",)
    assert right.kind == MaterialRouteKind.FIXED
    assert right.toolhead_ids == ("bambu:toolhead:0",)


def test_candidate5_physical_derived_fixtures_contain_no_sensitive_connection_keys() -> None:
    _assert_secret_safe(_load_fixture("candidate5_partial_initial_status.json"))
    _assert_secret_safe(_load_fixture("candidate5_incremental_material_sequence.json"))
