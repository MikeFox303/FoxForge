# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import ssl
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def certificate_fingerprint_sha256(der_certificate: bytes) -> str:
    """Return a stable SHA-256 fingerprint without exposing certificate contents."""

    return hashlib.sha256(der_certificate).hexdigest()


def tls_certificate_fingerprint(host: str, port: int, *, timeout: float = 5.0) -> str:
    """Read a peer certificate fingerprint without trusting the presented certificate."""

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with (
        socket.create_connection((host, port), timeout=timeout) as raw_socket,
        context.wrap_socket(raw_socket, server_hostname=host) as tls_socket,
    ):
        certificate = tls_socket.getpeercert(binary_form=True)
    if not certificate:
        raise RuntimeError("peer did not provide a TLS certificate")
    return certificate_fingerprint_sha256(certificate)


def _http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: object | None = None,
    timeout: float = 5.0,
) -> tuple[int, object | None]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator supplied validation target
            raw = response.read()
            return response.status, _decode_json(raw)
    except HTTPError as exc:
        return exc.code, _decode_json(exc.read())
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def _decode_json(raw: bytes) -> object | None:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _display_target(value: str, *, include_targets: bool) -> str:
    return value if include_targets else "redacted"


def probe_bambu(
    host: str,
    *,
    mqtt_port: int = 8883,
    ftps_port: int = 990,
    timeout: float = 5.0,
    include_targets: bool = False,
) -> dict[str, object]:
    result: dict[str, object] = {
        "kind": "bambu_tls",
        "target": _display_target(host, include_targets=include_targets),
        "mqttPort": mqtt_port,
        "ftpsPort": ftps_port,
    }
    try:
        mqtt_fingerprint = tls_certificate_fingerprint(host, mqtt_port, timeout=timeout)
        ftps_fingerprint = tls_certificate_fingerprint(host, ftps_port, timeout=timeout)
    except (OSError, RuntimeError, ssl.SSLError) as exc:
        result.update({"ok": False, "error": type(exc).__name__})
        return result

    result.update(
        {
            "ok": True,
            "mqttCertificateSha256": mqtt_fingerprint,
            "ftpsCertificateSha256": ftps_fingerprint,
            "sameCertificate": mqtt_fingerprint == ftps_fingerprint,
        }
    )
    return result


def probe_foxforge(
    base_url: str,
    *,
    command_token: str | None = None,
    timeout: float = 5.0,
    include_targets: bool = False,
) -> dict[str, object]:
    base = base_url.rstrip("/")
    result: dict[str, object] = {
        "kind": "foxforge",
        "target": _display_target(base, include_targets=include_targets),
    }
    try:
        health_status, health_payload = _http_json(f"{base}/healthz", timeout=timeout)
        result["healthStatus"] = health_status
        result["healthOk"] = (
            health_status == 200
            and isinstance(health_payload, dict)
            and health_payload.get("status") == "ok"
        )

        headers = {"Idempotency-Key": "physical-validation-auth-boundary"}
        if command_token:
            headers["Authorization"] = f"Bearer {command_token}"
        auth_status, auth_payload = _http_json(
            f"{base}/api/v1/inventory/spools",
            method="POST",
            headers=headers,
            payload={},
            timeout=timeout,
        )
        result["authBoundaryStatus"] = auth_status
        error_code = None
        if isinstance(auth_payload, dict):
            error = auth_payload.get("error")
            if isinstance(error, dict) and isinstance(error.get("code"), str):
                error_code = error["code"]
        result["authBoundaryCode"] = error_code

        if command_token:
            result["authBoundaryOk"] = auth_status == 400 and error_code == "invalid_request"
        else:
            result["authBoundaryOk"] = auth_status in {401, 503} and error_code in {
                "unauthorized",
                "command_api_disabled",
            }
        result["ok"] = bool(result["healthOk"] and result["authBoundaryOk"])
    except RuntimeError as exc:
        result.update({"ok": False, "error": type(exc).__name__})
    return result


def probe_moonraker(
    base_url: str,
    *,
    api_key: str | None = None,
    timeout: float = 5.0,
    include_targets: bool = False,
) -> dict[str, object]:
    base = base_url.rstrip("/")
    headers = {"X-Api-Key": api_key} if api_key else None
    result: dict[str, object] = {
        "kind": "moonraker",
        "target": _display_target(base, include_targets=include_targets),
    }
    try:
        status, payload = _http_json(f"{base}/server/info", headers=headers, timeout=timeout)
        result["status"] = status
        result["jsonResponse"] = isinstance(payload, dict)
        result["ok"] = status == 200 and isinstance(payload, dict)
    except RuntimeError as exc:
        result.update({"ok": False, "error": type(exc).__name__})
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect secret-safe FoxForge physical/deployment validation evidence as JSON."
    )
    parser.add_argument("--bambu-host", help="Bambu LAN host/IP to probe for MQTT/FTPS TLS certificates.")
    parser.add_argument("--bambu-mqtt-port", type=int, default=8883)
    parser.add_argument("--bambu-ftps-port", type=int, default=990)
    parser.add_argument("--moonraker-url", help="Moonraker base URL; probes /server/info.")
    parser.add_argument("--foxforge-url", help="FoxForge base URL through the deployment path being validated.")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--include-targets", action="store_true", help="Include host/URL values in JSON evidence.")
    parser.add_argument("--output", type=Path, help="Write JSON evidence to this path instead of stdout only.")
    parser.add_argument(
        "--foxforge-token-env",
        default="FOXFORGE_VALIDATION_COMMAND_TOKEN",
        help="Environment variable containing an optional FoxForge command token. The value is never printed.",
    )
    parser.add_argument(
        "--moonraker-api-key-env",
        default="FOXFORGE_VALIDATION_MOONRAKER_API_KEY",
        help="Environment variable containing an optional Moonraker API key. The value is never printed.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    probes: list[dict[str, object]] = []

    if args.bambu_host:
        probes.append(
            probe_bambu(
                args.bambu_host,
                mqtt_port=args.bambu_mqtt_port,
                ftps_port=args.bambu_ftps_port,
                timeout=args.timeout,
                include_targets=args.include_targets,
            )
        )
    if args.moonraker_url:
        probes.append(
            probe_moonraker(
                args.moonraker_url,
                api_key=os.environ.get(args.moonraker_api_key_env),
                timeout=args.timeout,
                include_targets=args.include_targets,
            )
        )
    if args.foxforge_url:
        probes.append(
            probe_foxforge(
                args.foxforge_url,
                command_token=os.environ.get(args.foxforge_token_env),
                timeout=args.timeout,
                include_targets=args.include_targets,
            )
        )

    if not probes:
        build_parser().error("at least one of --bambu-host, --moonraker-url or --foxforge-url is required")

    report: dict[str, Any] = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "secretValuesIncluded": False,
        "probes": probes,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")

    return 0 if all(bool(probe.get("ok")) for probe in probes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
