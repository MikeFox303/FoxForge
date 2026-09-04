# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Mapping

from foxforge.domain.printers import PrinterIdentity

from .adapter import BambuAdapter
from .certificate_trust import normalize_certificate_sha256
from .lan_transport import BambuLanTransport
from .lan_wire import BambuLanSettings


def create_bambu_lan_adapter(
    identity: PrinterIdentity,
    settings: Mapping[str, object],
) -> BambuAdapter:
    """Build a production Bambu LAN adapter from persisted settings."""
    if identity.adapter_kind != "bambu":
        raise ValueError("Bambu LAN factory requires identity.adapter_kind == 'bambu'")

    serial_number = _optional_string(settings.get("serial_number"), "serial_number") or identity.serial_number
    if not serial_number:
        raise ValueError("serial_number is required for Bambu LAN MQTT topics")

    transport = BambuLanTransport(
        BambuLanSettings(
            host=_required_string(settings, "host"),
            serial_number=serial_number,
            access_code=_required_string(settings, "access_code"),
            mqtt_port=_port(settings.get("mqtt_port", 8883), "mqtt_port"),
            ftps_port=_port(settings.get("ftps_port", 990), "ftps_port"),
            username=_optional_string(settings.get("username"), "username") or "bblp",
            connect_timeout_seconds=_positive_float(
                settings.get("connect_timeout_seconds", 10.0),
                "connect_timeout_seconds",
            ),
            command_timeout_seconds=_positive_float(
                settings.get("command_timeout_seconds", 15.0),
                "command_timeout_seconds",
            ),
            tls_verify=_boolean(settings.get("tls_verify", False), "tls_verify"),
            mqtt_tls_certificate_sha256=normalize_certificate_sha256(
                _optional_string(settings.get("mqtt_tls_certificate_sha256"), "mqtt_tls_certificate_sha256"),
                field_name="mqtt_tls_certificate_sha256",
            ),
            ftps_tls_certificate_sha256=normalize_certificate_sha256(
                _optional_string(settings.get("ftps_tls_certificate_sha256"), "ftps_tls_certificate_sha256"),
                field_name="ftps_tls_certificate_sha256",
            ),
        )
    )
    return BambuAdapter(identity, transport)


def _required_string(settings: Mapping[str, object], field_name: str) -> str:
    value = settings.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    stripped = value.strip()
    return stripped or None


def _positive_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be a positive number")
    number = float(value)
    if number <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return number


def _port(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
        raise ValueError(f"{field_name} must be a valid TCP port")
    return value


def _boolean(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value
