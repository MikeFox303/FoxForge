# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Low-level Bambu LAN MQTT and implicit-FTPS clients."""

from __future__ import annotations

import asyncio
import ftplib
import json
import socket
import ssl
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import paho.mqtt.client as mqtt

from .certificate_trust import normalize_certificate_sha256, verify_peer_certificate_sha256
from .transport import BambuTransportError, BambuTransportErrorKind

_UPLOAD_FLOOR_BYTES_PER_SECOND = 25 * 1024
_UPLOAD_MIN_TIMEOUT_SECONDS = 600.0
_UPLOAD_CHUNK_BYTES = 1024 * 1024
_UPLOAD_CONFIRM_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class BambuLanSettings:
    host: str
    serial_number: str
    access_code: str
    mqtt_port: int = 8883
    ftps_port: int = 990
    username: str = "bblp"
    connect_timeout_seconds: float = 10.0
    command_timeout_seconds: float = 15.0
    tls_verify: bool = False
    mqtt_tls_certificate_sha256: str | None = None
    ftps_tls_certificate_sha256: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("host", "serial_number", "access_code", "username"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        for field_name in ("mqtt_port", "ftps_port"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
                raise ValueError(f"{field_name} must be a valid TCP port")
        for field_name in ("connect_timeout_seconds", "command_timeout_seconds"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int | float) or float(value) <= 0:
                raise ValueError(f"{field_name} must be positive")
            object.__setattr__(self, field_name, float(value))
        object.__setattr__(
            self,
            "mqtt_tls_certificate_sha256",
            normalize_certificate_sha256(
                self.mqtt_tls_certificate_sha256,
                field_name="mqtt_tls_certificate_sha256",
            ),
        )
        object.__setattr__(
            self,
            "ftps_tls_certificate_sha256",
            normalize_certificate_sha256(
                self.ftps_tls_certificate_sha256,
                field_name="ftps_tls_certificate_sha256",
            ),
        )

    @property
    def report_topic(self) -> str:
        return f"device/{self.serial_number}/report"

    @property
    def request_topic(self) -> str:
        return f"device/{self.serial_number}/request"


class BambuMqttWire(Protocol):
    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def publish(self, payload: dict[str, object]) -> None: ...

    def messages(self) -> AsyncIterator[dict[str, object]]: ...


class BambuFtpsWire(Protocol):
    async def upload(self, local_path: Path, remote_filename: str) -> None: ...


class PahoBambuMqttWire:
    """Paho MQTT v3.1.1 client bridged into asyncio without blocking it."""

    def __init__(self, settings: BambuLanSettings) -> None:
        self._settings = settings
        self._client: mqtt.Client | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._messages: asyncio.Queue[dict[str, object] | BambuTransportError | None] = asyncio.Queue()
        self._connect_future: asyncio.Future[None] | None = None
        self._closing = False

    async def connect(self) -> None:
        if self._client is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._messages = asyncio.Queue()
        self._connect_future = self._loop.create_future()
        self._closing = False

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"foxforge-{self._settings.serial_number[-8:]}",
            protocol=mqtt.MQTTv311,
        )
        client.username_pw_set(self._settings.username, self._settings.access_code)
        client.tls_set_context(_tls_context(self._settings.tls_verify))
        client.reconnect_delay_set(min_delay=1, max_delay=10)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        self._client = client

        try:
            result = await asyncio.to_thread(
                client.connect,
                self._settings.host,
                self._settings.mqtt_port,
                60,
            )
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise BambuTransportError(
                    BambuTransportErrorKind.UNAVAILABLE,
                    f"Bambu MQTT connect returned rc={result}",
                    vendor_code=str(result),
                )
            client.loop_start()
            await asyncio.wait_for(self._connect_future, timeout=self._settings.connect_timeout_seconds)
        except TimeoutError as error:
            await self.disconnect()
            raise BambuTransportError(BambuTransportErrorKind.TIMEOUT, "Bambu MQTT connection timed out") from error
        except BambuTransportError:
            await self.disconnect()
            raise
        except OSError as error:
            await self.disconnect()
            raise BambuTransportError(BambuTransportErrorKind.UNAVAILABLE, str(error)) from error
        except Exception as error:
            await self.disconnect()
            raise BambuTransportError(BambuTransportErrorKind.INTERNAL, str(error)) from error

    async def disconnect(self) -> None:
        client = self._client
        if client is None:
            return
        self._closing = True
        self._client = None
        with suppress(RuntimeError):
            await asyncio.to_thread(client.disconnect)
        await asyncio.to_thread(client.loop_stop)
        self._messages.put_nowait(None)
        self._connect_future = None

    async def publish(self, payload: dict[str, object]) -> None:
        client = self._client
        if client is None:
            raise BambuTransportError(BambuTransportErrorKind.UNAVAILABLE, "Bambu MQTT is not connected")
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        info = client.publish(self._settings.request_topic, body, qos=1)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise BambuTransportError(
                BambuTransportErrorKind.UNAVAILABLE,
                f"Bambu MQTT publish returned rc={info.rc}",
                vendor_code=str(info.rc),
            )
        try:
            await asyncio.to_thread(info.wait_for_publish, timeout=self._settings.command_timeout_seconds)
        except RuntimeError as error:
            raise BambuTransportError(BambuTransportErrorKind.UNAVAILABLE, str(error)) from error
        if not info.is_published():
            raise BambuTransportError(
                BambuTransportErrorKind.TIMEOUT,
                "Bambu MQTT QoS1 publish acknowledgement timed out",
            )

    async def messages(self) -> AsyncIterator[dict[str, object]]:
        queue = self._messages
        while True:
            item = await queue.get()
            if item is None:
                return
            if isinstance(item, BambuTransportError):
                raise item
            yield item

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        code = _reason_code_value(reason_code)
        if code not in {0, None}:
            if code in {4, 5, 134, 135}:
                kind = BambuTransportErrorKind.AUTHENTICATION
            else:
                kind = BambuTransportErrorKind.REJECTED
            self._finish_connect(
                BambuTransportError(
                    kind,
                    f"Bambu MQTT connection rejected: {reason_code}",
                    vendor_code=str(code),
                )
            )
            return
        try:
            self._verify_mqtt_certificate(client)
        except BambuTransportError as error:
            self._finish_connect(error)
            return
        result, _mid = client.subscribe(self._settings.report_topic, qos=1)
        if result != mqtt.MQTT_ERR_SUCCESS:
            self._finish_connect(
                BambuTransportError(
                    BambuTransportErrorKind.UNAVAILABLE,
                    f"Bambu MQTT subscribe returned rc={result}",
                    vendor_code=str(result),
                )
            )
            return
        self._finish_connect(None)

    def _verify_mqtt_certificate(self, client: mqtt.Client) -> None:
        expected = self._settings.mqtt_tls_certificate_sha256
        if expected is None:
            return
        peer_socket = client.socket()
        if peer_socket is None or not hasattr(peer_socket, "getpeercert"):
            raise BambuTransportError(
                BambuTransportErrorKind.REJECTED,
                "Bambu MQTT TLS peer certificate is unavailable for pin verification",
                vendor_code="certificate_missing",
            )
        verify_peer_certificate_sha256(peer_socket, expected, service="MQTT")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        if self._closing:
            return
        code = _reason_code_value(reason_code)
        self._threadsafe_message(
            BambuTransportError(
                BambuTransportErrorKind.UNAVAILABLE,
                f"Bambu MQTT disconnected: {reason_code}",
                vendor_code=None if code is None else str(code),
            )
        )

    def _on_message(self, client, userdata, message) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if isinstance(payload, dict):
            self._threadsafe_message(payload)

    def _finish_connect(self, error: BambuTransportError | None) -> None:
        loop = self._loop
        future = self._connect_future
        if loop is None or future is None:
            return

        def finish() -> None:
            if future.done():
                return
            if error is None:
                future.set_result(None)
            else:
                future.set_exception(error)

        loop.call_soon_threadsafe(finish)

    def _threadsafe_message(self, item: dict[str, object] | BambuTransportError | None) -> None:
        loop = self._loop
        if loop is not None:
            loop.call_soon_threadsafe(self._messages.put_nowait, item)


class ImplicitFtpsBambuWire:
    """Upload files to the printer's implicit FTPS service (normally port 990)."""

    def __init__(self, settings: BambuLanSettings) -> None:
        self._settings = settings

    async def upload(self, local_path: Path, remote_filename: str) -> None:
        if Path(remote_filename).name != remote_filename or not remote_filename:
            raise BambuTransportError(BambuTransportErrorKind.REJECTED, "remote filename must be a plain basename")
        try:
            file_size = local_path.stat().st_size
        except OSError as error:
            raise BambuTransportError(BambuTransportErrorKind.REJECTED, str(error)) from error
        upload_timeout = max(
            _UPLOAD_MIN_TIMEOUT_SECONDS,
            self._settings.command_timeout_seconds,
            file_size / _UPLOAD_FLOOR_BYTES_PER_SECOND,
        )
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._upload_sync, local_path, remote_filename, file_size),
                timeout=upload_timeout,
            )
        except TimeoutError as error:
            raise BambuTransportError(BambuTransportErrorKind.TIMEOUT, "Bambu FTPS upload timed out") from error
        except BambuTransportError:
            raise
        except ftplib.error_perm as error:
            message = str(error)
            kind = (
                BambuTransportErrorKind.AUTHENTICATION
                if message.startswith("530")
                else BambuTransportErrorKind.REJECTED
            )
            raise BambuTransportError(kind, message) from error
        except ftplib.all_errors as error:
            raise BambuTransportError(BambuTransportErrorKind.UNAVAILABLE, str(error)) from error

    def _upload_sync(self, local_path: Path, remote_filename: str, file_size: int) -> None:
        context = _tls_context(self._settings.tls_verify)
        ftp = _ImplicitFTP_TLS(context=context, timeout=self._settings.connect_timeout_seconds)
        try:
            ftp.connect(
                self._settings.host,
                self._settings.ftps_port,
                timeout=self._settings.connect_timeout_seconds,
            )
            self._verify_ftps_certificate(ftp)
            ftp.login(self._settings.username, self._settings.access_code)
            ftp.prot_p()
            self._send_file(ftp, local_path, remote_filename)
            self._confirm_uploaded_file(ftp, remote_filename, file_size)
            with suppress(*ftplib.all_errors):
                ftp.quit()
        finally:
            with suppress(*ftplib.all_errors):
                ftp.close()

    def _verify_ftps_certificate(self, ftp: ftplib.FTP_TLS) -> None:
        expected = self._settings.ftps_tls_certificate_sha256
        if expected is None:
            return
        peer_socket = ftp.sock
        if peer_socket is None or not hasattr(peer_socket, "getpeercert"):
            raise BambuTransportError(
                BambuTransportErrorKind.REJECTED,
                "Bambu FTPS TLS peer certificate is unavailable for pin verification",
                vendor_code="certificate_missing",
            )
        verify_peer_certificate_sha256(peer_socket, expected, service="FTPS")

    def _send_file(self, ftp: ftplib.FTP_TLS, local_path: Path, remote_filename: str) -> None:
        data_connection = ftp.transfercmd(f"STOR {remote_filename}")
        data_connection.setblocking(True)
        data_connection.settimeout(self._settings.command_timeout_seconds)
        try:
            with local_path.open("rb") as handle:
                while chunk := handle.read(_UPLOAD_CHUNK_BYTES):
                    data_connection.sendall(chunk)
        finally:
            with suppress(OSError):
                data_connection.close()

    def _confirm_uploaded_file(self, ftp: ftplib.FTP_TLS, remote_filename: str, file_size: int) -> None:
        control_socket = ftp.sock
        previous_timeout = control_socket.gettimeout() if control_socket is not None else None
        try:
            if control_socket is not None:
                control_socket.settimeout(max(self._settings.command_timeout_seconds, _UPLOAD_CONFIRM_TIMEOUT_SECONDS))
            try:
                ftp.voidresp()
                return
            except (OSError, ftplib.Error, EOFError) as confirmation_error:
                server_size = _remote_size(ftp, remote_filename)
                if server_size == file_size:
                    return
                if isinstance(confirmation_error, ftplib.error_perm):
                    kind = BambuTransportErrorKind.REJECTED
                else:
                    kind = BambuTransportErrorKind.UNAVAILABLE
                detail = "unknown" if server_size is None else str(server_size)
                raise BambuTransportError(
                    kind,
                    f"Bambu FTPS upload was not confirmed; remote size={detail}, expected={file_size}",
                ) from confirmation_error
        finally:
            if control_socket is not None:
                with suppress(OSError):
                    control_socket.settimeout(previous_timeout)


class _ImplicitFTP_TLS(ftplib.FTP_TLS):
    """FTP_TLS variant that negotiates TLS immediately on the control socket."""

    def connect(
        self,
        host: str = "",
        port: int = 0,
        timeout: float | None = None,
        source_address: tuple[str, int] | None = None,
    ) -> str:
        if host:
            self.host = host
        if port:
            self.port = port
        if timeout is not None:
            self.timeout = timeout
        self.source_address = source_address
        self.sock = socket.create_connection(
            (self.host, self.port),
            self.timeout,
            source_address=self.source_address,
        )
        self.af = self.sock.family
        server_hostname = self.host if self.context.check_hostname else None
        self.sock = self.context.wrap_socket(self.sock, server_hostname=server_hostname)
        self.file = self.sock.makefile("r", encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome


def _remote_size(ftp: ftplib.FTP_TLS, remote_filename: str) -> int | None:
    try:
        size = ftp.size(remote_filename)
    except ftplib.all_errors:
        return None
    return size if isinstance(size, int) and size >= 0 else None


def _tls_context(verify: bool) -> ssl.SSLContext:
    if verify:
        return ssl.create_default_context()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _reason_code_value(reason_code: object) -> int | None:
    value = getattr(reason_code, "value", reason_code)
    return value if isinstance(value, int) else None
