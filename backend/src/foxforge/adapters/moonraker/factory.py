# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Mapping

from foxforge.domain.printers import PrinterIdentity

from .adapter import MoonrakerAdapter
from .http_transport import MoonrakerHttpSettings, MoonrakerHttpTransport


def create_moonraker_http_adapter(
    identity: PrinterIdentity,
    settings: Mapping[str, object],
) -> MoonrakerAdapter:
    """Build a production Moonraker adapter from persisted composition settings."""
    if identity.adapter_kind != "moonraker":
        raise ValueError("Moonraker factory requires identity.adapter_kind == 'moonraker'")

    base_url = _required_string(settings, "base_url")
    api_key = _optional_string(settings.get("api_key"), field_name="api_key")
    request_timeout_seconds = _positive_float(settings.get("request_timeout_seconds", 10.0), "request_timeout_seconds")

    transport = MoonrakerHttpTransport(
        MoonrakerHttpSettings(
            base_url=base_url,
            api_key=api_key,
            request_timeout_seconds=request_timeout_seconds,
        )
    )
    return MoonrakerAdapter(identity, transport)


def _required_string(settings: Mapping[str, object], field_name: str) -> str:
    value = settings.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_string(value: object, *, field_name: str) -> str | None:
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
