# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import pytest

from foxforge.adapters.bambu import BambuAdapter, create_bambu_lan_adapter
from foxforge.domain.printers import PrinterIdentity
from foxforge.domain.printers.capabilities import PrintExecutionCapability


def _identity(*, adapter_kind: str = "bambu", serial_number: str | None = "01P00FOXFORGE") -> PrinterIdentity:
    return PrinterIdentity(
        printer_id="bambu-production-1",
        display_name="Bambu printer",
        vendor="bambu_lab",
        model="X2D",
        serial_number=serial_number,
        adapter_kind=adapter_kind,
    )


def test_factory_builds_registry_ready_production_adapter() -> None:
    identity = _identity()
    adapter = create_bambu_lan_adapter(
        identity,
        {
            "host": "192.0.2.30",
            "access_code": " 12345678 ",
            "mqtt_port": 8883,
            "ftps_port": 990,
            "connect_timeout_seconds": 4,
            "command_timeout_seconds": 6,
            "tls_verify": False,
        },
    )

    assert isinstance(adapter, BambuAdapter)
    assert adapter.identity is identity
    assert adapter.capability(PrintExecutionCapability) is not None
    assert adapter.snapshot().printer_id == identity.printer_id


def test_factory_accepts_serial_from_settings_when_identity_has_none() -> None:
    adapter = create_bambu_lan_adapter(
        _identity(serial_number=None),
        {
            "host": "printer.local",
            "serial_number": "01P00OVERRIDE",
            "access_code": "12345678",
        },
    )

    assert isinstance(adapter, BambuAdapter)


def test_factory_normalizes_serial_for_case_sensitive_mqtt_topics() -> None:
    adapter = create_bambu_lan_adapter(
        _identity(serial_number=None),
        {
            "host": "printer.local",
            "serial_number": " 01p00x2dtest ",
            "access_code": "12345678",
        },
    )

    assert adapter._transport._settings.serial_number == "01P00X2DTEST"  # noqa: SLF001
    assert adapter._transport._settings.report_topic == "device/01P00X2DTEST/report"  # noqa: SLF001


def test_factory_requires_host_access_code_and_serial() -> None:
    with pytest.raises(ValueError, match="host"):
        create_bambu_lan_adapter(_identity(), {"access_code": "12345678"})

    with pytest.raises(ValueError, match="access_code"):
        create_bambu_lan_adapter(_identity(), {"host": "printer.local"})

    with pytest.raises(ValueError, match="serial_number"):
        create_bambu_lan_adapter(
            _identity(serial_number=None),
            {"host": "printer.local", "access_code": "12345678"},
        )


def test_factory_rejects_wrong_adapter_kind() -> None:
    with pytest.raises(ValueError, match="adapter_kind"):
        create_bambu_lan_adapter(
            _identity(adapter_kind="moonraker"),
            {"host": "printer.local", "access_code": "12345678"},
        )


def test_factory_rejects_bool_for_numeric_settings() -> None:
    with pytest.raises(ValueError, match="mqtt_port"):
        create_bambu_lan_adapter(
            _identity(),
            {"host": "printer.local", "access_code": "12345678", "mqtt_port": True},
        )

    with pytest.raises(ValueError, match="command_timeout_seconds"):
        create_bambu_lan_adapter(
            _identity(),
            {
                "host": "printer.local",
                "access_code": "12345678",
                "command_timeout_seconds": True,
            },
        )
