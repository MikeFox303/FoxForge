# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json

from foxforge.domain.printers import PrinterIdentity
from foxforge.infrastructure.secrets import FileSecretStore
from foxforge.runtime.config import (
    CONFIG_SCHEMA_VERSION,
    PrinterRuntimeConfig,
    RuntimeConfig,
    load_runtime_config,
    save_runtime_config,
)
from foxforge.runtime.secret_settings import hydrate_settings, migrate_legacy_runtime_secrets


def _identity(adapter_kind: str, printer_id: str) -> PrinterIdentity:
    return PrinterIdentity(
        printer_id=printer_id,
        display_name=printer_id,
        vendor="test",
        model=None,
        serial_number=None,
        adapter_kind=adapter_kind,
    )


def test_legacy_inline_secrets_move_out_of_runtime_config_and_hydrate(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    store = FileSecretStore(tmp_path / "secrets.json")
    bambu = _identity("bambu", "x2d-main")
    moonraker = _identity("moonraker", "ender-ke")
    save_runtime_config(
        config_path,
        RuntimeConfig(
            schema_version=CONFIG_SCHEMA_VERSION,
            printers=(
                PrinterRuntimeConfig(
                    identity=bambu,
                    settings={"host": "192.168.1.20", "access_code": "bambu-secret"},
                ),
                PrinterRuntimeConfig(
                    identity=moonraker,
                    settings={"base_url": "http://192.168.1.30:7125", "api_key": "moonraker-secret"},
                ),
            ),
        ),
    )

    migrated = migrate_legacy_runtime_secrets(config_path, load_runtime_config(config_path), store)

    raw = config_path.read_text(encoding="utf-8")
    assert "bambu-secret" not in raw
    assert "moonraker-secret" not in raw
    assert "access_code" not in raw
    assert "api_key" not in raw
    assert (tmp_path / "config.json.backup-pre-secret-store").is_file()
    backup = (tmp_path / "config.json.backup-pre-secret-store").read_text(encoding="utf-8")
    assert "bambu-secret" in backup
    assert "moonraker-secret" in backup

    bambu_settings = hydrate_settings(bambu, migrated.printers[0].settings, store)
    moonraker_settings = hydrate_settings(moonraker, migrated.printers[1].settings, store)
    assert bambu_settings["access_code"] == "bambu-secret"
    assert moonraker_settings["api_key"] == "moonraker-secret"
    assert json.loads((tmp_path / "secrets.json").read_text(encoding="utf-8"))["version"] == 1


def test_config_without_inline_secret_does_not_create_migration_backup(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    store = FileSecretStore(tmp_path / "secrets.json")
    identity = _identity("moonraker", "ender-ke")
    config = RuntimeConfig(
        schema_version=CONFIG_SCHEMA_VERSION,
        printers=(
            PrinterRuntimeConfig(
                identity=identity,
                settings={"base_url": "http://192.168.1.30:7125"},
            ),
        ),
    )
    save_runtime_config(config_path, config)

    migrated = migrate_legacy_runtime_secrets(config_path, load_runtime_config(config_path), store)

    assert migrated == config
    assert not (tmp_path / "config.json.backup-pre-secret-store").exists()
    assert not (tmp_path / "secrets.json").exists()
