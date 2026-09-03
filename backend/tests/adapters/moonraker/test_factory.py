# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import pytest

from foxforge.adapters.moonraker import MoonrakerAdapter, create_moonraker_http_adapter
from foxforge.domain.printers import PrinterIdentity
from foxforge.domain.printers.capabilities import PrintExecutionCapability


def _identity(*, adapter_kind: str = "moonraker") -> PrinterIdentity:
    return PrinterIdentity(
        printer_id="moonraker-production-1",
        display_name="Ender 3 V3 KE",
        vendor="creality",
        model="Ender-3 V3 KE",
        serial_number=None,
        adapter_kind=adapter_kind,
    )


def test_factory_builds_registry_ready_production_adapter() -> None:
    identity = _identity()
    adapter = create_moonraker_http_adapter(
        identity,
        {
            "base_url": "http://printer.local:7125/",
            "api_key": " secret ",
            "request_timeout_seconds": 5,
        },
    )

    assert isinstance(adapter, MoonrakerAdapter)
    assert adapter.identity is identity
    assert adapter.capability(PrintExecutionCapability) is not None
    assert adapter.snapshot().printer_id == identity.printer_id


def test_factory_requires_base_url() -> None:
    with pytest.raises(ValueError, match="base_url"):
        create_moonraker_http_adapter(_identity(), {})


def test_factory_rejects_wrong_adapter_kind() -> None:
    with pytest.raises(ValueError, match="adapter_kind"):
        create_moonraker_http_adapter(_identity(adapter_kind="bambu"), {"base_url": "http://printer.local:7125"})


def test_factory_rejects_invalid_timeout_type() -> None:
    with pytest.raises(ValueError, match="request_timeout_seconds"):
        create_moonraker_http_adapter(
            _identity(),
            {"base_url": "http://printer.local:7125", "request_timeout_seconds": True},
        )
