"""Minimal BambuTunnelLocal (:6000) transport for internal eMMC uploads.

This module is intentionally transport-only. It does not alter Bambuddy's
scheduler or MQTT dispatch by merely being imported.

Protocol implementation is derived from the independently reverse-engineered
AGPL-3.0 work in ClusterM/open-bamboo-networking, in particular
``tools/bambu6000_client.py`` and ``research/06.04-port-6000.md`` (2026).
FoxForge is licensed under AGPL-3.0-only; the referenced implementation was
published under AGPL-compatible terms.

Bambu's newer printer families use this TLS service for the internal eMMC
storage path that Bambu Studio addresses as ``brtc://emmc/<name>``. Legacy
Bambuddy queue dispatch is FTPS-only; this transport is the prerequisite for
supporting stick-less X2D dispatch without changing the existing FTPS path for
other printers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import socket
import ssl
import struct
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PORT = 6000
MAGIC_LOGIN = 0x0101013F
MAGIC_CTRL = 0x0102013F
MTYPE_CTRL_SETUP = 12291
MTYPE_CTRL_JSON = 12289
RESULT_OK = 0
RESULT_CONTINUE = 1
RESULT_FILE_EXISTS = 19
DEFAULT_CLIENT_VERSION = "02.03.00.00"

ProgressCallback = Callable[[int, int], None]


class BambuTunnelError(OSError):
    """Raised when the local :6000 session or operation fails."""


@dataclass(frozen=True, slots=True)
class TunnelReply:
    magic: int
    sequence: int
    body: bytes

    def json(self) -> dict[str, Any]:
        raw = self.body.split(b"\n\n", 1)[0]
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BambuTunnelError("printer returned a non-JSON tunnel reply") from exc
        if not isinstance(value, dict):
            raise BambuTunnelError("printer returned a non-object tunnel reply")
        return value


def _frame_header(payload_len: int, magic: int, sequence: int) -> bytes:
    if payload_len < 0:
        raise ValueError("payload_len must be >= 0")
    return struct.pack("<IIII", payload_len, magic, sequence & 0xFFFFFFFF, 0)


def _login_payload(username: str, access_code: str) -> bytes:
    user = username.encode("ascii", errors="strict")[:8].ljust(8, b"\0")
    code = access_code.encode("ascii", errors="strict")[:8].ljust(8, b"\0")
    return user + code


def _compact_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def _wrap_ctrl(value: dict[str, Any]) -> bytes:
    if "mtype" not in value:
        value = {"mtype": MTYPE_CTRL_JSON, **value}
    return _compact_json(value)


def _recv_exact(sock: ssl.SSLSocket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise BambuTunnelError("printer closed the :6000 TLS session")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _recv_frame(sock: ssl.SSLSocket) -> TunnelReply:
    header = _recv_exact(sock, 16)
    payload_len, magic, sequence, _reserved = struct.unpack("<IIII", header)
    if payload_len > 64 * 1024 * 1024:
        raise BambuTunnelError(f"unreasonable tunnel frame length: {payload_len}")
    body = _recv_exact(sock, payload_len) if payload_len else b""
    return TunnelReply(magic=magic, sequence=sequence, body=body)


def _send_frame(sock: ssl.SSLSocket, magic: int, sequence: int, payload: bytes) -> None:
    sock.sendall(_frame_header(len(payload), magic, sequence))
    if payload:
        sock.sendall(payload)


def _tls_socket(host: str, *, port: int, timeout: float) -> ssl.SSLSocket:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    raw = socket.create_connection((host, port), timeout=timeout)
    try:
        tls = context.wrap_socket(raw, server_hostname=host)
    except Exception:
        raw.close()
        raise
    tls.settimeout(timeout)
    return tls


def _file_md5(path: Path) -> str:
    digest = hashlib.md5()  # nosec B324 - protocol requires MD5 as a transfer checksum
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest().lower()


class BambuTunnelSession:
    """Synchronous BambuTunnelLocal session focused on file transfer."""

    def __init__(
        self,
        host: str,
        access_code: str,
        *,
        port: int = PORT,
        timeout: float = 15.0,
        username: str = "bblp",
        client_version: str = DEFAULT_CLIENT_VERSION,
        sock: ssl.SSLSocket | None = None,
        sequence_seed: int | None = None,
    ) -> None:
        self.host = host
        self.access_code = access_code
        self.port = port
        self.timeout = timeout
        self.username = username
        self.client_version = client_version
        self._sock = sock
        self._frame_sequence = sequence_seed or random.randint(1, 0x7FFFFFFF)
        self._command_sequence = 1
        self._ready = False

    @property
    def pid(self) -> str:
        return f"{self._frame_sequence & 0xFFFFFFFF:08x}"

    def _next_frame_sequence(self) -> int:
        value = self._frame_sequence
        self._frame_sequence += 1
        return value

    def _next_command_sequence(self) -> int:
        value = self._command_sequence
        self._command_sequence += 1
        return value

    def connect(self) -> None:
        if self._ready:
            return
        if self._sock is None:
            self._sock = _tls_socket(self.host, port=self.port, timeout=self.timeout)

        _send_frame(
            self._sock,
            MAGIC_LOGIN,
            self._next_frame_sequence(),
            _login_payload(self.username, self.access_code),
        )
        login_reply = _recv_frame(self._sock)
        if ((login_reply.magic >> 16) & 0xFF) != 0x01:
            raise BambuTunnelError(f"unexpected login reply magic 0x{login_reply.magic:08x}")

        setup = {
            "sequence": 0,
            "mtype": MTYPE_CTRL_SETUP,
            "req": {
                "t_av": 1,
                "mtype": MTYPE_CTRL_JSON,
                "peer_t": 3,
                "pid": self.pid,
                "ver": self.client_version,
            },
        }
        _send_frame(self._sock, MAGIC_CTRL, self._next_frame_sequence(), _compact_json(setup))
        setup_reply = _recv_frame(self._sock).json()
        if int(setup_reply.get("result", 0)) not in (RESULT_OK, RESULT_CONTINUE):
            raise BambuTunnelError(f"tunnel setup failed: {setup_reply}")
        self._ready = True

    def close(self) -> None:
        self._ready = False
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self) -> BambuTunnelSession:
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _send_ctrl(self, payload: dict[str, Any]) -> None:
        if not self._ready or self._sock is None:
            raise BambuTunnelError("tunnel session is not connected")
        _send_frame(self._sock, MAGIC_CTRL, self._next_frame_sequence(), _wrap_ctrl(payload))

    def _recv_json(self) -> dict[str, Any]:
        if not self._ready or self._sock is None:
            raise BambuTunnelError("tunnel session is not connected")
        return _recv_frame(self._sock).json()

    def media_ability(self) -> dict[str, Any]:
        """Read the :6000 media/storage ability without changing printer state."""
        sequence = self._next_command_sequence()
        self._send_ctrl(
            {
                "cmdtype": 7,
                "sequence": sequence,
                "req": {"peer": "studio", "api_version": 2},
            }
        )
        reply = self._recv_json()
        result = int(reply.get("result", -1))
        if result not in (RESULT_OK, RESULT_CONTINUE):
            raise BambuTunnelError(f"media ability failed result={result}: {reply}")
        return reply

    def upload_file(
        self,
        local_path: str | Path,
        remote_name: str,
        *,
        storage: str = "emmc",
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Upload *local_path* using the native chunked FILE_UPLOAD command."""
        path = Path(local_path)
        total = path.stat().st_size
        if total <= 0:
            raise BambuTunnelError("cannot upload an empty file")
        remote_name = Path(remote_name).name
        if not remote_name:
            raise BambuTunnelError("remote filename is empty")

        checksum = _file_md5(path)
        sequence = self._next_command_sequence()
        self._send_ctrl(
            {
                "cmdtype": 5,
                "sequence": sequence,
                "req": {
                    "type": "model",
                    "storage": storage,
                    "path": remote_name,
                    "total": total,
                },
            }
        )
        init_reply = self._recv_json()
        init_result = int(init_reply.get("result", -1))
        if init_result not in (RESULT_CONTINUE, RESULT_FILE_EXISTS):
            raise BambuTunnelError(f"upload init failed result={init_result}: {init_reply}")

        info = init_reply.get("reply") or {}
        chunk_kib = int(info.get("chunk_size") or 0)
        offset = int(info.get("offset") or 0)
        if chunk_kib <= 0:
            raise BambuTunnelError(f"upload init returned invalid chunk_size: {chunk_kib}")
        if offset < 0 or offset > total:
            raise BambuTunnelError(f"upload init returned invalid offset: {offset}")

        chunk_size = chunk_kib * 1024
        frag_id = offset // chunk_size
        if progress_callback:
            progress_callback(offset, total)

        with path.open("rb") as handle:
            handle.seek(offset)
            while offset < total:
                chunk = handle.read(min(chunk_size, total - offset))
                if not chunk:
                    raise BambuTunnelError("local file ended before advertised size")
                end = offset + len(chunk)
                req: dict[str, Any] = {
                    "frag_id": frag_id,
                    "offset": offset,
                    "size": len(chunk),
                }
                if end >= total:
                    req["file_md5"] = checksum
                body = _wrap_ctrl({"cmdtype": 5, "sequence": sequence, "req": req})
                payload = body + b"\n\n" + chunk
                assert self._sock is not None
                _send_frame(self._sock, MAGIC_CTRL, self._next_frame_sequence(), payload)
                offset = end
                frag_id += 1
                if progress_callback:
                    progress_callback(offset, total)

        final_reply = self._recv_json()
        final_result = int(final_reply.get("result", -1))
        if final_result not in (RESULT_OK, RESULT_FILE_EXISTS):
            raise BambuTunnelError(f"upload failed result={final_result}: {final_reply}")

    def delete_file(self, remote_name: str, *, storage: str = "emmc") -> None:
        """Delete one uploaded file by basename from the selected storage."""
        remote_name = Path(remote_name).name
        sequence = self._next_command_sequence()
        self._send_ctrl(
            {
                "cmdtype": 3,
                "sequence": sequence,
                "req": {"delete": [remote_name], "storage": storage},
            }
        )
        reply = self._recv_json()
        result = int(reply.get("result", -1))
        if result not in (RESULT_OK, RESULT_CONTINUE, RESULT_FILE_EXISTS):
            raise BambuTunnelError(f"delete failed result={result}: {reply}")


def upload_internal_file(
    host: str,
    access_code: str,
    local_path: str | Path,
    remote_name: str,
    *,
    timeout: float = 15.0,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """One-shot helper used by an async adapter via ``asyncio.to_thread``."""
    with BambuTunnelSession(host, access_code, timeout=timeout) as session:
        session.upload_file(
            local_path,
            remote_name,
            storage="emmc",
            progress_callback=progress_callback,
        )


def delete_internal_file(
    host: str,
    access_code: str,
    remote_name: str,
    *,
    timeout: float = 15.0,
) -> None:
    with BambuTunnelSession(host, access_code, timeout=timeout) as session:
        session.delete_file(remote_name, storage="emmc")
