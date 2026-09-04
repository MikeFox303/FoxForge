# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
import os
from contextlib import suppress
from pathlib import Path


class FileSecretStore:
    """Small atomic JSON secret store for the private FoxForge data volume."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def get(self, key: str) -> str | None:
        return self._read().get(_validated_key(key))

    def set(self, key: str, value: str) -> None:
        normalized_key = _validated_key(key)
        if not isinstance(value, str) or not value:
            raise ValueError("secret value must be a non-empty string")
        payload = self._read()
        payload[normalized_key] = value
        self._write(payload)

    def delete(self, key: str) -> None:
        normalized_key = _validated_key(key)
        payload = self._read()
        if normalized_key not in payload:
            return
        payload.pop(normalized_key)
        self._write(payload)

    def _read(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"unable to read FoxForge secret store: {self._path}") from error
        if not isinstance(raw, dict) or raw.get("version") != 1 or not isinstance(raw.get("secrets"), dict):
            raise ValueError("FoxForge secret store has an unsupported format")
        result: dict[str, str] = {}
        for key, value in raw["secrets"].items():
            if not isinstance(key, str) or not isinstance(value, str) or not value:
                raise ValueError("FoxForge secret store contains an invalid entry")
            result[key] = value
        return result

    def _write(self, secrets: dict[str, str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        payload = {"version": 1, "secrets": dict(sorted(secrets.items()))}
        try:
            temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            _restrict_permissions(temporary)
            os.replace(temporary, self._path)
            _restrict_permissions(self._path)
        finally:
            with suppress(OSError):
                temporary.unlink()


def _validated_key(key: str) -> str:
    if not isinstance(key, str) or not key.strip():
        raise ValueError("secret key must be a non-empty string")
    normalized = key.strip()
    if len(normalized) > 512 or any(ord(character) < 0x20 for character in normalized):
        raise ValueError("secret key is invalid")
    return normalized


def _restrict_permissions(path: Path) -> None:
    if os.name == "nt":
        return
    with suppress(OSError):
        path.chmod(0o600)
