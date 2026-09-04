# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from pathlib import Path


def test_frontend_renders_exactly_one_printer_setup_launcher_tree() -> None:
    root = Path(__file__).resolve().parents[3]
    main = (root / "frontend/src/main.tsx").read_text(encoding="utf-8")
    app = (root / "frontend/src/FoxForgeApp.tsx").read_text(encoding="utf-8")

    assert (main + app).count("<PrinterSetupLauncher") == 1
