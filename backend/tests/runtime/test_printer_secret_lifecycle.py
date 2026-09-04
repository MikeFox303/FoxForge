# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

from foxforge.application.fleet import FleetService
from foxforge.application.printer_management import PrinterConfiguration
from foxforge.application.secrets import InMemorySecretStore
from foxforge.domain.printers import PrinterIdentity
from foxforge.infrastructure.printers import AdapterRegistry
from foxforge.runtime.config import CONFIG_SCHEMA_VERSION, RuntimeConfig, load_runtime_config
from foxforge.runtime.printer_manager import RuntimePrinterManager
from foxforge.runtime.secret_settings import secret_key
from foxforge.testing import FakePrinterAdapter


def _configuration(*, access_code: str | None = "first-secret") -> PrinterConfiguration:
    settings: dict[str, object] = {"host": "192.168.1.20"}
    if access_code is not None:
        settings["access_code"] = access_code
    return PrinterConfiguration(
        identity=PrinterIdentity(
            printer_id="x2d-main",
            display_name="Bambu X2D",
            vendor="bambu_lab",
            model="X2D",
            serial_number="SERIAL",
            adapter_kind="bambu",
        ),
        settings=settings,
    )


def test_add_update_and_remove_keep_secret_out_of_runtime_config(tmp_path) -> None:
    async def scenario() -> None:
        config_path = tmp_path / "config.json"
        fleet = FleetService()
        registry = AdapterRegistry()
        registry.register("bambu", lambda identity, settings: FakePrinterAdapter(identity))
        secrets = InMemorySecretStore()
        manager = RuntimePrinterManager(
            fleet=fleet,
            registry=registry,
            config_path=config_path,
            config=RuntimeConfig(schema_version=CONFIG_SCHEMA_VERSION, printers=()),
            secret_store=secrets,
        )
        secret = secret_key(_configuration().identity, "access_code")
        try:
            await manager.add(_configuration())
            persisted = load_runtime_config(config_path).printers[0]
            assert "access_code" not in persisted.settings
            assert secrets.get(secret) == "first-secret"
            assert manager.configuration("x2d-main").settings["access_code"] == "first-secret"

            await manager.update("x2d-main", _configuration(access_code=None))
            assert secrets.get(secret) == "first-secret"
            assert "access_code" not in load_runtime_config(config_path).printers[0].settings

            await manager.update("x2d-main", _configuration(access_code="second-secret"))
            assert secrets.get(secret) == "second-secret"
            assert manager.configuration("x2d-main").settings["access_code"] == "second-secret"

            await manager.remove("x2d-main")
            assert secrets.get(secret) is None
            assert load_runtime_config(config_path).printers == ()
        finally:
            await fleet.aclose()

    asyncio.run(scenario())
