# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path

import pytest

from foxforge.runtime import load_runtime_config

_FIXTURES = Path(__file__).parents[1] / "fixtures" / "persistence"


def test_missing_runtime_config_creates_safe_empty_template(tmp_path) -> None:
    path = tmp_path / "data" / "config.json"

    config = load_runtime_config(path)

    assert config.schema_version == 2
    assert config.printers == ()
    assert json.loads(path.read_text(encoding="utf-8")) == {"schemaVersion": 2, "printers": []}
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_runtime_config_v1_fixture_migrates_to_v2_with_exact_backup(tmp_path) -> None:
    path = tmp_path / "config.json"
    fixture = _FIXTURES / "config-v1.json"
    shutil.copyfile(fixture, path)
    original = path.read_bytes()

    config = load_runtime_config(path)

    assert config.schema_version == 2
    assert config.printers[0].identity.printer_id == "x2d-main"
    assert config.printers[0].settings["access_code"] == "fixture-secret"
    assert json.loads(path.read_text(encoding="utf-8"))["schemaVersion"] == 2
    backup = tmp_path / "config.json.backup-v1"
    assert backup.read_bytes() == original

    backup_before_restart = backup.read_bytes()
    restarted = load_runtime_config(path)
    assert restarted == config
    assert backup.read_bytes() == backup_before_restart


def test_runtime_config_parses_current_bambu_and_moonraker_without_exposing_vendor_types(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "printers": [
                    {
                        "printerId": "x2d-main",
                        "displayName": "Bambu X2D",
                        "vendor": "bambu_lab",
                        "model": "X2D",
                        "serialNumber": "SERIAL123",
                        "adapterKind": "bambu",
                        "settings": {"host": "192.0.2.10", "access_code": "secret"},
                    },
                    {
                        "printerId": "ender-ke",
                        "displayName": "Ender 3 V3 KE",
                        "vendor": "creality",
                        "model": "Ender 3 V3 KE",
                        "serialNumber": None,
                        "adapterKind": "moonraker",
                        "settings": {"base_url": "http://192.0.2.20:7125"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    config = load_runtime_config(path)

    assert [printer.identity.printer_id for printer in config.printers] == ["x2d-main", "ender-ke"]
    assert config.printers[0].identity.adapter_kind == "bambu"
    assert config.printers[0].settings["access_code"] == "secret"
    assert config.printers[1].identity.adapter_kind == "moonraker"


def test_runtime_config_rejects_duplicate_printer_ids(tmp_path) -> None:
    path = tmp_path / "config.json"
    printer = {
        "printerId": "duplicate",
        "displayName": "Printer",
        "vendor": "test",
        "adapterKind": "moonraker",
        "settings": {"base_url": "http://127.0.0.1:7125"},
    }
    path.write_text(
        json.dumps({"schemaVersion": 2, "printers": [printer, printer]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate printerId"):
        load_runtime_config(path)


def test_runtime_config_rejects_future_schema_without_mutation(tmp_path) -> None:
    path = tmp_path / "config.json"
    original = json.dumps({"schemaVersion": 99, "printers": []})
    path.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError, match="newer than supported"):
        load_runtime_config(path)

    assert path.read_text(encoding="utf-8") == original
    assert not (tmp_path / "config.json.backup-v99").exists()


def test_corrupt_runtime_config_is_not_replaced_or_backed_up(tmp_path) -> None:
    path = tmp_path / "config.json"
    original = "{not-json"
    path.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError, match="unable to read"):
        load_runtime_config(path)

    assert path.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob("config.json.backup-*")) == []
