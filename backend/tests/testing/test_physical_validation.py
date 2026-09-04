# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from foxforge.testing import physical_validation


def test_certificate_fingerprint_sha256_is_stable() -> None:
    assert (
        physical_validation.certificate_fingerprint_sha256(b"foxforge-test-certificate")
        == "571c05b8f8f0b30b3d6e074f650c90c716a05c8c933a269ba70aaf6dbb436659"
    )


def test_targets_are_redacted_by_default() -> None:
    assert physical_validation._display_target("192.0.2.42", include_targets=False) == "redacted"
    assert physical_validation._display_target("192.0.2.42", include_targets=True) == "192.0.2.42"


def test_foxforge_probe_never_returns_command_token(monkeypatch) -> None:
    token = "validation-command-token-0123456789abcdef"
    calls: list[tuple[str, dict[str, str] | None]] = []

    def fake_http_json(
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        payload: object | None = None,
        timeout: float = 5.0,
    ) -> tuple[int, object | None]:
        del method, payload, timeout
        calls.append((url, headers))
        if url.endswith("/healthz"):
            return 200, {"status": "ok", "apiVersion": "1"}
        return 400, {"error": {"code": "invalid_request"}}

    monkeypatch.setattr(physical_validation, "_http_json", fake_http_json)

    result = physical_validation.probe_foxforge("http://127.0.0.1:8000", command_token=token)

    assert result["ok"] is True
    assert result["target"] == "redacted"
    assert token not in repr(result)
    assert calls[1][1] is not None
    assert calls[1][1]["Authorization"] == f"Bearer {token}"


def test_foxforge_probe_accepts_truthful_read_only_boundary(monkeypatch) -> None:
    def fake_http_json(
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        payload: object | None = None,
        timeout: float = 5.0,
    ) -> tuple[int, object | None]:
        del method, headers, payload, timeout
        if url.endswith("/healthz"):
            return 200, {"status": "ok", "apiVersion": "1"}
        return 503, {"error": {"code": "command_api_disabled"}}

    monkeypatch.setattr(physical_validation, "_http_json", fake_http_json)

    result = physical_validation.probe_foxforge("http://127.0.0.1:8000")

    assert result["ok"] is True
    assert result["authBoundaryStatus"] == 503
    assert result["authBoundaryCode"] == "command_api_disabled"


def test_bambu_probe_records_independent_service_fingerprints(monkeypatch) -> None:
    def fake_fingerprint(host: str, port: int, *, timeout: float = 5.0) -> str:
        del host, timeout
        return "a" * 64 if port == 8883 else "b" * 64

    monkeypatch.setattr(physical_validation, "tls_certificate_fingerprint", fake_fingerprint)

    result = physical_validation.probe_bambu("192.0.2.10")

    assert result["ok"] is True
    assert result["mqttCertificateSha256"] == "a" * 64
    assert result["ftpsCertificateSha256"] == "b" * 64
    assert result["sameCertificate"] is False
    assert result["target"] == "redacted"
