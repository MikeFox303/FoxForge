# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from foxforge.domain.printers import PrinterIdentity

_CONFIG_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PrinterRuntimeConfig:
    identity: PrinterIdentity
    settings: dict[str, object]


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    schema_version: int
    printers: tuple[PrinterRuntimeConfig, ...]


def load_runtime_config(path: Path | str) -> RuntimeConfig:
    """Load the local composition configuration, creating a safe empty file when absent."""
    config_path = Path(path)
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps({"schemaVersion": _CONFIG_SCHEMA_VERSION, "printers": []}, indent=2) + "\n",
            encoding="utf-8",
        )
        _restrict_permissions(config_path)

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"unable to read FoxForge runtime config: {config_path}") from error

    if not isinstance(raw, dict):
        raise ValueError("runtime config must be a JSON object")
    if raw.get("schemaVersion") != _CONFIG_SCHEMA_VERSION:
        raise ValueError(f"runtime config schemaVersion must be {_CONFIG_SCHEMA_VERSION}")

    raw_printers = raw.get("printers")
    if not isinstance(raw_printers, list):
        raise ValueError("runtime config printers must be an array")

    printers: list[PrinterRuntimeConfig] = []
    seen_ids: set[str] = set()
    for index, value in enumerate(raw_printers):
        printer = _parse_printer(value, index=index)
        printer_id = printer.identity.printer_id
        if printer_id in seen_ids:
            raise ValueError(f"duplicate printerId in runtime config: {printer_id}")
        seen_ids.add(printer_id)
        printers.append(printer)

    return RuntimeConfig(schema_version=_CONFIG_SCHEMA_VERSION, printers=tuple(printers))


def _parse_printer(value: object, *, index: int) -> PrinterRuntimeConfig:
    if not isinstance(value, dict):
        raise ValueError(f"printers[{index}] must be an object")

    identity = PrinterIdentity(
        printer_id=_required_string(value, "printerId", index=index),
        display_name=_required_string(value, "displayName", index=index),
        vendor=_required_string(value, "vendor", index=index),
        model=_optional_string(value.get("model"), field_name="model", index=index),
        serial_number=_optional_string(value.get("serialNumber"), field_name="serialNumber", index=index),
        adapter_kind=_required_string(value, "adapterKind", index=index),
    )

    settings = value.get("settings", {})
    if not isinstance(settings, dict):
        raise ValueError(f"printers[{index}].settings must be an object")
    return PrinterRuntimeConfig(identity=identity, settings=_json_mapping(settings, index=index))


def _json_mapping(settings: dict[object, object], *, index: int) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in settings.items():
        if not isinstance(key, str):
            raise ValueError(f"printers[{index}].settings keys must be strings")
        if not _is_json_value(value):
            raise ValueError(f"printers[{index}].settings.{key} must contain JSON-compatible data")
        normalized[key] = value
    return normalized


def _is_json_value(value: object) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


def _required_string(value: dict[str, Any], field_name: str, *, index: int) -> str:
    candidate = value.get(field_name)
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError(f"printers[{index}].{field_name} must be a non-empty string")
    return candidate.strip()


def _optional_string(value: object, *, field_name: str, index: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"printers[{index}].{field_name} must be a string or null")
    stripped = value.strip()
    return stripped or None


def _restrict_permissions(path: Path) -> None:
    if os.name == "nt":
        return
    try:
        path.chmod(0o600)
    except OSError:
        # Some mounted filesystems do not support chmod. The container/storage
        # boundary must still restrict access to the application's data volume.
        pass
