from __future__ import annotations

import hashlib
import json
import struct
from collections import deque

import pytest

from bambu_tunnel_local import (
    MAGIC_CTRL,
    MAGIC_LOGIN,
    MTYPE_CTRL_JSON,
    MTYPE_CTRL_SETUP,
    BambuTunnelError,
    BambuTunnelSession,
    _frame_header,
    _login_payload,
    _wrap_ctrl,
)

SERVER_LOGIN_MAGIC = 0x0001013F
SERVER_CTRL_MAGIC = 0x0002013F


def _server_frame(body: bytes, *, magic: int = SERVER_CTRL_MAGIC, sequence: int = 1) -> bytes:
    return struct.pack("<IIII", len(body), magic, sequence, 0) + body


def _json_frame(value: dict, *, sequence: int = 1) -> bytes:
    return _server_frame(json.dumps(value, separators=(",", ":")).encode(), sequence=sequence)


def _decode_client_frames(writes: list[bytes]):
    assert len(writes) % 2 == 0
    frames = []
    for index in range(0, len(writes), 2):
        header, body = writes[index], writes[index + 1]
        payload_len, magic, sequence, reserved = struct.unpack("<IIII", header)
        assert payload_len == len(body)
        assert reserved == 0
        frames.append((magic, sequence, body))
    return frames


class ScriptedSocket:
    def __init__(self, replies: list[bytes]):
        self._recv = deque(replies)
        self.writes: list[bytes] = []
        self.timeline: list[str] = []
        self.closed = False

    def sendall(self, data: bytes):
        self.timeline.append("send")
        self.writes.append(bytes(data))

    def recv(self, size: int) -> bytes:
        self.timeline.append("recv")
        if not self._recv:
            return b""
        chunk = self._recv[0]
        if len(chunk) <= size:
            self._recv.popleft()
            return chunk
        self._recv[0] = chunk[size:]
        return chunk[:size]

    def close(self):
        self.closed = True


@pytest.fixture
def handshake_replies():
    return [
        _server_frame(b"\0\0\0\0", magic=SERVER_LOGIN_MAGIC),
        _json_frame({"mtype": MTYPE_CTRL_SETUP, "sequence": 0, "result": 0, "reply": {}}),
    ]


def test_frame_header_is_16_byte_little_endian():
    header = _frame_header(0x11223344, MAGIC_CTRL, 0x55667788)
    assert len(header) == 16
    assert header == struct.pack("<IIII", 0x11223344, MAGIC_CTRL, 0x55667788, 0)


def test_login_payload_is_exactly_two_padded_eight_byte_fields():
    payload = _login_payload("bblp", "12345678")
    assert len(payload) == 16
    assert payload[:8] == b"bblp\0\0\0\0"
    assert payload[8:] == b"12345678"


def test_wrap_ctrl_injects_mtype_once():
    wrapped = json.loads(_wrap_ctrl({"cmdtype": 7, "sequence": 1, "req": {}}))
    assert wrapped["mtype"] == MTYPE_CTRL_JSON
    assert wrapped["cmdtype"] == 7

    explicit = json.loads(_wrap_ctrl({"mtype": 999, "cmdtype": 7}))
    assert explicit["mtype"] == 999


def test_connect_sends_login_then_ctrl_setup(handshake_replies):
    sock = ScriptedSocket(handshake_replies)
    session = BambuTunnelSession("192.0.2.10", "12345678", sock=sock, sequence_seed=100)

    session.connect()
    frames = _decode_client_frames(sock.writes)

    assert frames[0][0] == MAGIC_LOGIN
    assert frames[0][2] == _login_payload("bblp", "12345678")
    assert frames[1][0] == MAGIC_CTRL
    setup = json.loads(frames[1][2])
    assert setup["mtype"] == MTYPE_CTRL_SETUP
    assert setup["sequence"] == 0
    assert setup["req"]["mtype"] == MTYPE_CTRL_JSON
    assert setup["req"]["peer_t"] == 3
    assert setup["req"]["t_av"] == 1
    assert setup["req"]["ver"] == "02.03.00.00"
    assert len(setup["req"]["pid"]) == 8


def test_media_ability_is_read_only_request(handshake_replies):
    replies = handshake_replies + [
        _json_frame(
            {"mtype": MTYPE_CTRL_JSON, "cmdtype": 7, "sequence": 1, "result": 0, "reply": {"storage": ["emmc"]}}
        )
    ]
    sock = ScriptedSocket(replies)
    session = BambuTunnelSession("192.0.2.10", "12345678", sock=sock, sequence_seed=50)
    session.connect()

    reply = session.media_ability()
    assert reply["result"] == 0
    assert reply["reply"]["storage"] == ["emmc"]


def test_chunked_upload_pipelines_all_chunks_before_terminal_read(tmp_path, handshake_replies):
    data = bytes(range(256)) * 10
    local = tmp_path / "tiny.3mf"
    local.write_bytes(data)

    replies = handshake_replies + [
        _json_frame(
            {
                "mtype": MTYPE_CTRL_JSON,
                "cmdtype": 5,
                "sequence": 1,
                "result": 1,
                "reply": {"chunk_size": 1, "offset": 0},
            }
        ),
        _json_frame({"mtype": MTYPE_CTRL_JSON, "cmdtype": 5, "sequence": 1, "result": 0}),
    ]
    sock = ScriptedSocket(replies)
    progress: list[tuple[int, int]] = []
    session = BambuTunnelSession("192.0.2.10", "12345678", sock=sock, sequence_seed=10)
    session.connect()
    timeline_before = len(sock.timeline)

    session.upload_file(
        local,
        "../unsafe/tiny.3mf",
        progress_callback=lambda done, total: progress.append((done, total)),
    )

    frames = _decode_client_frames(sock.writes)
    upload_frames = frames[2:]
    assert len(upload_frames) == 4

    init = json.loads(upload_frames[0][2])
    assert init["cmdtype"] == 5
    assert init["req"] == {
        "type": "model",
        "storage": "emmc",
        "path": "tiny.3mf",
        "total": len(data),
    }

    reconstructed = bytearray()
    for frag_id, (_magic, _frame_seq, payload) in enumerate(upload_frames[1:]):
        meta_raw, chunk = payload.split(b"\n\n", 1)
        meta = json.loads(meta_raw)
        assert meta["mtype"] == MTYPE_CTRL_JSON
        assert meta["cmdtype"] == 5
        assert meta["sequence"] == init["sequence"]
        assert meta["req"]["frag_id"] == frag_id
        assert meta["req"]["offset"] == len(reconstructed)
        assert meta["req"]["size"] == len(chunk)
        reconstructed.extend(chunk)
        if frag_id < 2:
            assert "file_md5" not in meta["req"]
        else:
            assert meta["req"]["file_md5"] == hashlib.md5(data).hexdigest()  # nosec B324

    assert bytes(reconstructed) == data
    assert progress == [(0, len(data)), (1024, len(data)), (2048, len(data)), (len(data), len(data))]

    ops = sock.timeline[timeline_before:]
    assert ops == [
        "send",
        "send",
        "recv",
        "recv",
        "send",
        "send",
        "send",
        "send",
        "send",
        "send",
        "recv",
        "recv",
    ]


def test_upload_accepts_file_exists_init_as_overwrite(tmp_path, handshake_replies):
    local = tmp_path / "overwrite.3mf"
    local.write_bytes(b"abc")
    replies = handshake_replies + [
        _json_frame(
            {
                "mtype": MTYPE_CTRL_JSON,
                "cmdtype": 5,
                "sequence": 1,
                "result": 19,
                "reply": {"chunk_size": 255, "offset": 0},
            }
        ),
        _json_frame({"mtype": MTYPE_CTRL_JSON, "cmdtype": 5, "sequence": 1, "result": 0}),
    ]
    sock = ScriptedSocket(replies)
    session = BambuTunnelSession("192.0.2.10", "12345678", sock=sock)
    session.connect()
    session.upload_file(local, "overwrite.3mf")


def test_upload_bad_init_result_raises_before_sending_data(tmp_path, handshake_replies):
    local = tmp_path / "blocked.3mf"
    local.write_bytes(b"payload")
    replies = handshake_replies + [
        _json_frame({"mtype": MTYPE_CTRL_JSON, "cmdtype": 5, "sequence": 1, "result": -9203, "reply": {}}),
    ]
    sock = ScriptedSocket(replies)
    session = BambuTunnelSession("192.0.2.10", "12345678", sock=sock)
    session.connect()

    with pytest.raises(BambuTunnelError, match="upload init failed"):
        session.upload_file(local, "blocked.3mf")

    assert len(_decode_client_frames(sock.writes)) == 3


def test_final_upload_error_is_not_silently_accepted(tmp_path, handshake_replies):
    local = tmp_path / "bad-final.3mf"
    local.write_bytes(b"payload")
    replies = handshake_replies + [
        _json_frame(
            {
                "mtype": MTYPE_CTRL_JSON,
                "cmdtype": 5,
                "sequence": 1,
                "result": 1,
                "reply": {"chunk_size": 255, "offset": 0},
            }
        ),
        _json_frame({"mtype": MTYPE_CTRL_JSON, "cmdtype": 5, "sequence": 1, "result": -9203}),
    ]
    sock = ScriptedSocket(replies)
    session = BambuTunnelSession("192.0.2.10", "12345678", sock=sock)
    session.connect()

    with pytest.raises(BambuTunnelError, match="upload failed"):
        session.upload_file(local, "bad-final.3mf")
