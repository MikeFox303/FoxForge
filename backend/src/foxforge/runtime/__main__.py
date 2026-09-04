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

    app = create_runtime_app(
        RuntimeSettings(
            data_dir=data_dir,
            config_path=config_path,
            static_dir=static_dir,
            reconnect_seconds=reconnect_seconds,
            command_token=command_token,
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
    try:
        value = float(raw)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a positive number") from error
    if value <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return value


if __name__ == "__main__":
    main()
