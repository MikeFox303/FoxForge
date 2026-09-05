# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from foxforge.adapters.bambu import (
    BambuLanSettings,
    BambuLanTransport,
    BambuTransportError,
    BambuTransportErrorKind,
)


class _NoInitialStateMqttWire:
    def __init__(self) -> None:
        self.connected = False
        self.published: list[dict[str, object]] = []
        self._messages: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        if self.connected:
            self.connected = False
            await self._messages.put(None)

    async def publish(self, payload: dict[str, object]) -> None:
        self.published.append(payload)
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
        # Deliberately do not answer pushall. This models a broker connection
        # that succeeded while the selected report topic never yields state.

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


def test_initial_state_timeout_has_stable_diagnostic_stage_code() -> None:
    async def scenario() -> None:
        settings = BambuLanSettings(
            host="192.0.2.10",
            serial_number="01P00FOXFORGE",
            access_code="12345678",
            connect_timeout_seconds=0.01,
        )
        mqtt = _NoInitialStateMqttWire()
        transport = BambuLanTransport(settings, mqtt_wire=mqtt, ftps_wire=_UnusedFtpsWire())

        try:
            await transport.connect()
        except BambuTransportError as error:
            assert error.kind == BambuTransportErrorKind.TIMEOUT
            assert error.vendor_code == "initial_state_timeout"
            assert mqtt.connected is False
        else:
            raise AssertionError("connection should fail without initial push_status")

    asyncio.run(scenario())
