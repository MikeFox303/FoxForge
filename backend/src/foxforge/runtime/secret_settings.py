# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import shutil
from contextlib import suppress
from dataclasses import replace
from pathlib import Path

from foxforge.application.secrets import SecretStore
from foxforge.domain.printers import PrinterIdentity

from .config import PrinterRuntimeConfig, RuntimeConfig, save_runtime_config

_SECRET_FIELDS: dict[str, tuple[str, ...]] = {
    "bambu": ("access_code",),
    "moonraker": ("api_key",),
}


def secret_fields(identity: PrinterIdentity) -> tuple[str, ...]:
    return _SECRET_FIELDS.get(identity.adapter_kind, ())


def secret_key(identity: PrinterIdentity, field_name: str) -> str:
    if field_name not in secret_fields(identity):
        raise ValueError(f"{field_name} is not a secret field for adapter {identity.adapter_kind}")
    return f"printer/{identity.printer_id}/{field_name}"


def hydrate_settings(
    identity: PrinterIdentity,
    settings: dict[str, object],
    store: SecretStore,
) -> dict[str, object]:
    hydrated = dict(settings)
    for field_name in secret_fields(identity):
        secret = store.get(secret_key(identity, field_name))
        if secret is not None:
            hydrated[field_name] = secret
    return hydrated


def persist_secret_settings(
    identity: PrinterIdentity,
    settings: dict[str, object],
    store: SecretStore,
) -> dict[str, object]:
    persisted = dict(settings)
    for field_name in secret_fields(identity):
        value = persisted.pop(field_name, None)
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field_name} must be a non-empty string when supplied")
        store.set(secret_key(identity, field_name), value)
    return persisted


def delete_printer_secrets(identity: PrinterIdentity, store: SecretStore) -> None:
    for field_name in secret_fields(identity):
        store.delete(secret_key(identity, field_name))


def migrate_legacy_runtime_secrets(
    config_path: Path,
    config: RuntimeConfig,
    store: SecretStore,
) -> RuntimeConfig:
    """Move legacy inline credentials to SecretStore and rewrite config atomically."""

    changed = False
    migrated: list[PrinterRuntimeConfig] = []
    for printer in config.printers:
        settings = dict(printer.settings)
        secret_names = secret_fields(printer.identity)
        if any(field_name in settings for field_name in secret_names):
            changed = True
            settings = persist_secret_settings(printer.identity, settings, store)
        migrated.append(PrinterRuntimeConfig(identity=printer.identity, settings=settings))

    if not changed:
        return config

    _ensure_sensitive_migration_backup(config_path)
    updated = replace(config, printers=tuple(migrated))
    save_runtime_config(config_path, updated)
    return updated


def _ensure_sensitive_migration_backup(config_path: Path) -> Path:
    backup_path = config_path.with_name(f"{config_path.name}.backup-pre-secret-store")
    if backup_path.exists():
        return backup_path
    try:
        shutil.copyfile(config_path, backup_path)
    except OSError as error:
        raise ValueError(f"unable to create secret-migration backup: {backup_path}") from error
    if backup_path.exists():
        with suppress(OSError):
            backup_path.chmod(0o600)
    return backup_path
