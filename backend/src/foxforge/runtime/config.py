# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
import os
import shutil
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from foxforge.domain.printers import PrinterIdentity

CONFIG_SCHEMA_VERSION = 2
_MIN_CONFIG_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PrinterRuntimeConfig:
    identity: PrinterIdentity
    settings: dict[str, object]


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    schema_version: int
    printers: tuple[PrinterRuntimeConfig, ...]


def load_runtime_config(path: Path | str) -> RuntimeConfig:
    """Load and safely migrate app-owned composition data."""
    config_path = Path(path)
    if not config_path.exists():
        save_runtime_config(
            config_path,
            RuntimeConfig(schema_version=CONFIG_SCHEMA_VERSION, printers=()),
        )

    raw = _read_config_object(config_path)
    version = raw.get("schemaVersion")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ValueError("runtime config schemaVersion must be an integer")
    if version > CONFIG_SCHEMA_VERSION:
        raise ValueError(
            f"runtime config schemaVersion {version} is newer than supported version {CONFIG_SCHEMA_VERSION}"
        )
    if version < _MIN_CONFIG_SCHEMA_VERSION:
        raise ValueError(f"unsupported runtime config schemaVersion: {version}")

    if version < CONFIG_SCHEMA_VERSION:
        raw = _migrate_runtime_config(config_path, raw, version)

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

    return RuntimeConfig(schema_version=CONFIG_SCHEMA_VERSION, printers=tuple(printers))


def save_runtime_config(path: Path | str, config: RuntimeConfig) -> None:
    """Atomically persist the app-owned runtime configuration.

    Printer credentials remain in the private application data volume, but the
    file is an implementation detail managed by FoxForge rather than a user
    configuration surface.
    """

    if config.schema_version != CONFIG_SCHEMA_VERSION:
        raise ValueError(f"runtime config schema_version must be {CONFIG_SCHEMA_VERSION}")

    seen_ids: set[str] = set()
    payload_printers: list[dict[str, object]] = []
    for printer in config.printers:
        printer_id = printer.identity.printer_id
        if printer_id in seen_ids:
            raise ValueError(f"duplicate printerId in runtime config: {printer_id}")
        seen_ids.add(printer_id)
        payload_printers.append(_encode_printer(printer))

    _atomic_write_config(
        Path(path),
        {"schemaVersion": CONFIG_SCHEMA_VERSION, "printers": payload_printers},
    )


def _migrate_runtime_config(config_path: Path, raw: dict[str, object], version: int) -> dict[str, object]:
    current = dict(raw)
    current_version = version
    while current_version < CONFIG_SCHEMA_VERSION:
        if current_version == 1:
            _ensure_config_backup(config_path, version=1)
            # v2 establishes explicit migration ownership. The printer payload
            # itself remains unchanged, so credentials and identities survive
            # the first migration byte-for-byte except for JSON formatting and
            # the schema marker.
            current["schemaVersion"] = 2
            current_version = 2
            continue
        raise ValueError(f"no runtime config migration path from schemaVersion {current_version}")

    _atomic_write_config(config_path, current)
    return _read_config_object(config_path)


def _ensure_config_backup(config_path: Path, *, version: int) -> Path:
    backup_path = config_path.with_name(f"{config_path.name}.backup-v{version}")
    if backup_path.exists():
        # A recovery point from an interrupted migration is never silently
        # overwritten. Reuse it and continue with atomic migration.
        return backup_path
    try:
        shutil.copyfile(config_path, backup_path)
    except OSError as error:
        raise ValueError(f"unable to create runtime config backup: {backup_path}") from error
    _restrict_permissions(backup_path)
    return backup_path


def _read_config_object(config_path: Path) -> dict[str, object]:
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"unable to read FoxForge runtime config: {config_path}") from error
    if not isinstance(raw, dict):
        raise ValueError("runtime config must be a JSON object")
    return raw


def _atomic_write_config(config_path: Path, payload: dict[str, object]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = config_path.with_name(f".{config_path.name}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        _restrict_permissions(temporary)
        os.replace(temporary, config_path)
        _restrict_permissions(config_path)
    finally:
        with suppress(OSError):
            temporary.unlink()


def _encode_printer(printer: PrinterRuntimeConfig) -> dict[str, object]:
    identity = printer.identity
    return {
        "printerId": identity.printer_id,
        "displayName": identity.display_name,
        "vendor": identity.vendor,
        "model": identity.model,
        "serialNumber": identity.serial_number,
        "adapterKind": identity.adapter_kind,
        "settings": _json_mapping(printer.settings, index=0),
    }


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
    # Some mounted filesystems do not support chmod. The container/storage
    # boundary must still restrict access to the application's data volume.
    with suppress(OSError):
        path.chmod(0o600)
