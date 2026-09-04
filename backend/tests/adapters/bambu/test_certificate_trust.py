# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib

import pytest

from foxforge.adapters.bambu.certificate_trust import (
    normalize_certificate_sha256,
    peer_certificate_sha256,
    verify_peer_certificate_sha256,
)
from foxforge.adapters.bambu.transport import BambuTransportError


class _Socket:
    def __init__(self, certificate: bytes) -> None:
        self._certificate = certificate

    def getpeercert(self, binary_form: bool = False):
        return self._certificate if binary_form else {}


def test_certificate_fingerprint_normalizes_colon_form() -> None:
    raw = "AA:" * 31 + "AA"
    assert normalize_certificate_sha256(raw, field_name="pin") == "aa" * 32


def test_certificate_fingerprint_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        normalize_certificate_sha256("not-a-pin", field_name="pin")


def test_peer_certificate_hash_and_match() -> None:
    certificate = b"certificate-der"
    expected = hashlib.sha256(certificate).hexdigest()
    socket = _Socket(certificate)

    assert peer_certificate_sha256(socket) == expected
    verify_peer_certificate_sha256(socket, expected, service="MQTT")


def test_peer_certificate_mismatch_is_rejected_without_exposing_fingerprints() -> None:
    expected = hashlib.sha256(b"expected").hexdigest()
    with pytest.raises(BambuTransportError) as caught:
        verify_peer_certificate_sha256(_Socket(b"actual"), expected, service="MQTT")

    assert caught.value.vendor_code == "certificate_mismatch"
    assert expected not in caught.value.message
    assert hashlib.sha256(b"actual").hexdigest() not in caught.value.message
