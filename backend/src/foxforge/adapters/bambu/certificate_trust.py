# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
from typing import Protocol

from .transport import BambuTransportError, BambuTransportErrorKind


class PeerCertificateSocket(Protocol):
    def getpeercert(self, binary_form: bool = False) -> bytes | dict[str, object]: ...


def normalize_certificate_sha256(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    normalized = value.strip().lower().replace(":", "")
    if not normalized:
        return None
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{field_name} must contain a SHA-256 certificate fingerprint")
    return normalized


def peer_certificate_sha256(sock: PeerCertificateSocket) -> str:
    certificate = sock.getpeercert(binary_form=True)
    if not isinstance(certificate, bytes) or not certificate:
        raise BambuTransportError(
            BambuTransportErrorKind.REJECTED,
            "Bambu TLS peer did not provide a certificate",
            vendor_code="certificate_missing",
        )
    return hashlib.sha256(certificate).hexdigest()


def verify_peer_certificate_sha256(
    sock: PeerCertificateSocket,
    expected_sha256: str | None,
    *,
    service: str,
) -> None:
    if expected_sha256 is None:
        return
    actual = peer_certificate_sha256(sock)
    if actual != expected_sha256:
        raise BambuTransportError(
            BambuTransportErrorKind.REJECTED,
            f"Bambu {service} TLS certificate fingerprint does not match the configured pin",
            vendor_code="certificate_mismatch",
        )
