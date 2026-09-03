# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import ftplib
from pathlib import Path

import pytest

from foxforge.adapters.bambu import BambuLanSettings, BambuTransportError
from foxforge.adapters.bambu import lan_wire


class _FakeSocket:
    def __init__(self) -> None:
        self.timeout: float | None = 10.0
        self.timeouts: list[float | None] = []

    def gettimeout(self) -> float | None:
        return self.timeout

    def settimeout(self, value: float | None) -> None:
        self.timeout = value
        self.timeouts.append(value)


class _FakeDataConnection:
    def __init__(self) -> None:
        self.blocking: bool | None = None
        self.timeout: float | None = None
        self.payload = bytearray()
        self.closed = False

    def setblocking(self, value: bool) -> None:
        self.blocking = value

    def settimeout(self, value: float) -> None:
        self.timeout = value

    def sendall(self, chunk: bytes) -> None:
        self.payload.extend(chunk)

    def close(self) -> None:
        self.closed = True


class _FakeImplicitFtps:
    def __init__(self, *, remote_size: int | None = None, voidresp_error: Exception | None = None) -> None:
        self.sock = _FakeSocket()
        self.data_connection = _FakeDataConnection()
        self.remote_size = remote_size
        self.voidresp_error = voidresp_error
        self.connected: tuple[str, int, float | None] | None = None
        self.credentials: tuple[str, str] | None = None
        self.protected = False
        self.transfer_command: str | None = None
        self.quit_called = False
        self.close_called = False

    def connect(self, host: str, port: int, timeout: float | None = None) -> str:
        self.connected = (host, port, timeout)
        return "220 ready"

    def login(self, username: str, password: str) -> str:
        self.credentials = (username, password)
        return "230 logged in"

    def prot_p(self) -> str:
        self.protected = True
        return "200 protected"

    def transfercmd(self, command: str) -> _FakeDataConnection:
        self.transfer_command = command
        return self.data_connection

    def voidresp(self) -> str:
        if self.voidresp_error is not None:
            raise self.voidresp_error
        return "226 Transfer complete"

    def size(self, remote_filename: str) -> int | None:
        return self.remote_size

    def quit(self) -> str:
        self.quit_called = True
        return "221 bye"

    def close(self) -> None:
        self.close_called = True


def _settings() -> BambuLanSettings:
    return BambuLanSettings(
        host="192.0.2.20",
        serial_number="01P00FOXFORGE",
        access_code="12345678",
        connect_timeout_seconds=2.0,
        command_timeout_seconds=3.0,
    )


def _install_fake(monkeypatch: pytest.MonkeyPatch, fake: _FakeImplicitFtps) -> None:
    monkeypatch.setattr(lan_wire, "_ImplicitFTP_TLS", lambda **kwargs: fake)


def test_ftps_upload_uses_manual_transfer_and_waits_for_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"foxforge-3mf" * 8192
    source = tmp_path / "job.3mf"
    source.write_bytes(payload)
    fake = _FakeImplicitFtps()
    _install_fake(monkeypatch, fake)

    asyncio.run(lan_wire.ImplicitFtpsBambuWire(_settings()).upload(source, "job.3mf"))

    assert fake.connected == ("192.0.2.20", 990, 2.0)
    assert fake.credentials == ("bblp", "12345678")
    assert fake.protected is True
    assert fake.transfer_command == "STOR job.3mf"
    assert bytes(fake.data_connection.payload) == payload
    assert fake.data_connection.blocking is True
    assert fake.data_connection.timeout == 3.0
    assert fake.data_connection.closed is True
    assert 60.0 in fake.sock.timeouts
    assert fake.quit_called is True
    assert fake.close_called is True


def test_ftps_accepts_ambiguous_426_only_when_remote_size_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"PK\x03\x04verified-bambu-upload"
    source = tmp_path / "verified.3mf"
    source.write_bytes(payload)
    fake = _FakeImplicitFtps(
        remote_size=len(payload),
        voidresp_error=ftplib.error_temp("426 Failure reading network stream"),
    )
    _install_fake(monkeypatch, fake)

    asyncio.run(lan_wire.ImplicitFtpsBambuWire(_settings()).upload(source, "verified.3mf"))

    assert bytes(fake.data_connection.payload) == payload
    assert fake.quit_called is True


def test_ftps_rejects_unconfirmed_short_remote_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"PK\x03\x04must-not-print-partial"
    source = tmp_path / "partial.3mf"
    source.write_bytes(payload)
    fake = _FakeImplicitFtps(
        remote_size=len(payload) - 3,
        voidresp_error=ftplib.error_temp("426 Failure reading network stream"),
    )
    _install_fake(monkeypatch, fake)

    with pytest.raises(BambuTransportError):
        asyncio.run(lan_wire.ImplicitFtpsBambuWire(_settings()).upload(source, "partial.3mf"))

    assert fake.quit_called is False
    assert fake.close_called is True
