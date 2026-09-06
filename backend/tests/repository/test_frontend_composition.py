# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from pathlib import Path


def test_frontend_renders_exactly_one_printer_setup_launcher_tree() -> None:
    root = Path(__file__).resolve().parents[3]
    paths = (
        "frontend/src/main.tsx",
        "frontend/src/FoxForgeApp.tsx",
        "frontend/src/app/AppShell.tsx",
    )
    composition = "\n".join((root / path).read_text(encoding="utf-8") for path in paths)

    assert composition.count("<PrinterSetupLauncher") == 1


def test_shell_owns_navigation_and_operator_chrome() -> None:
    root = Path(__file__).resolve().parents[3]
    shell = (root / "frontend/src/app/AppShell.tsx").read_text(encoding="utf-8")
    app = (root / "frontend/src/FoxForgeApp.tsx").read_text(encoding="utf-8")

    assert "<aside className=\"sidebar\">" in shell
    assert "<header className=\"topbar\">" in shell
    assert "<OperatorAccess" in shell
    assert "<aside className=\"sidebar\">" not in app
    assert "<OperatorAccess" not in app
