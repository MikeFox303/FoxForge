# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import logging
import os
from pathlib import Path

from aiohttp import web

from .app import RuntimeSettings, create_runtime_app


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("FOXFORGE_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    data_dir = Path(os.environ.get("FOXFORGE_DATA_DIR", "/data"))
    config_path = Path(os.environ.get("FOXFORGE_CONFIG", str(data_dir / "config.json")))
    static_value = os.environ.get("FOXFORGE_STATIC_DIR")
    static_dir = Path(static_value) if static_value else None
    host = os.environ.get("FOXFORGE_HOST", "0.0.0.0")
    port = _port(os.environ.get("FOXFORGE_PORT", "8000"))
    reconnect_seconds = _positive_float(
        os.environ.get("FOXFORGE_RECONNECT_SECONDS", "15"),
        field_name="FOXFORGE_RECONNECT_SECONDS",
    )
    command_token = os.environ.get("FOXFORGE_COMMAND_TOKEN")
    trusted_browser_sessions = _boolean_env(
        os.environ.get("FOXFORGE_TRUSTED_BROWSER_SESSIONS", "false"),
        field_name="FOXFORGE_TRUSTED_BROWSER_SESSIONS",
    )
    artifact_total_quota_bytes = _positive_int(
        os.environ.get("FOXFORGE_ARTIFACT_QUOTA_BYTES", str(20 * 1024 * 1024 * 1024)),
        field_name="FOXFORGE_ARTIFACT_QUOTA_BYTES",
    )
    artifact_min_free_bytes = _nonnegative_int(
        os.environ.get("FOXFORGE_ARTIFACT_MIN_FREE_BYTES", str(1024 * 1024 * 1024)),
        field_name="FOXFORGE_ARTIFACT_MIN_FREE_BYTES",
    )
    artifact_orphan_retention_seconds = _nonnegative_float(
        os.environ.get("FOXFORGE_ARTIFACT_ORPHAN_RETENTION_SECONDS", str(7 * 24 * 60 * 60)),
        field_name="FOXFORGE_ARTIFACT_ORPHAN_RETENTION_SECONDS",
    )
    artifact_temp_retention_seconds = _nonnegative_float(
        os.environ.get("FOXFORGE_ARTIFACT_TEMP_RETENTION_SECONDS", str(60 * 60)),
        field_name="FOXFORGE_ARTIFACT_TEMP_RETENTION_SECONDS",
    )

    app = create_runtime_app(
        RuntimeSettings(
            data_dir=data_dir,
            config_path=config_path,
            static_dir=static_dir,
            reconnect_seconds=reconnect_seconds,
            command_token=command_token,
            trusted_browser_sessions=trusted_browser_sessions,
            artifact_total_quota_bytes=artifact_total_quota_bytes,
            artifact_min_free_bytes=artifact_min_free_bytes,
            artifact_orphan_retention_seconds=artifact_orphan_retention_seconds,
            artifact_temp_retention_seconds=artifact_temp_retention_seconds,
        )
    )
    web.run_app(app, host=host, port=port, print=lambda line: logging.getLogger("foxforge.runtime").info("%s", line))


def _port(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError("FOXFORGE_PORT must be an integer") from error
    if not 1 <= value <= 65535:
        raise ValueError("FOXFORGE_PORT must be a valid TCP port")
    return value


def _positive_float(raw: str, *, field_name: str) -> float:
    value = _number(raw, field_name=field_name)
    if value <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return value


def _nonnegative_float(raw: str, *, field_name: str) -> float:
    value = _number(raw, field_name=field_name)
    if value < 0:
        raise ValueError(f"{field_name} must be a non-negative number")
    return value


def _number(raw: str, *, field_name: str) -> float:
    try:
        return float(raw)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a number") from error


def _positive_int(raw: str, *, field_name: str) -> int:
    value = _integer(raw, field_name=field_name)
    if value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _nonnegative_int(raw: str, *, field_name: str) -> int:
    value = _integer(raw, field_name=field_name)
    if value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _integer(raw: str, *, field_name: str) -> int:
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an integer") from error


def _boolean_env(raw: str, *, field_name: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{field_name} must be true or false")


if __name__ == "__main__":
    main()
