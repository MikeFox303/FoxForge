# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
import os

import pytest

from foxforge.infrastructure.secrets import FileSecretStore


def test_file_secret_store_round_trip_and_delete(tmp_path) -> None:
    path = tmp_path / "secrets.json"
    store = FileSecretStore(path)

    assert store.get("printer/p1/access_code") is None
    store.set("printer/p1/access_code", "12345678")
    assert store.get("printer/p1/access_code") == "12345678"

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "version": 1,
        "secrets": {"printer/p1/access_code": "12345678"},
    }
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600

    store.delete("printer/p1/access_code")
    assert store.get("printer/p1/access_code") is None


def test_file_secret_store_rejects_invalid_or_corrupt_data(tmp_path) -> None:
    path = tmp_path / "secrets.json"
    store = FileSecretStore(path)

    with pytest.raises(ValueError, match="non-empty"):
        store.set("printer/p1/api_key", "")

    path.write_text('{"version":2,"secrets":{}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported format"):
        store.get("printer/p1/api_key")
