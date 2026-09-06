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

    assert '<aside className="sidebar">' in shell
    assert '<header className="topbar">' in shell
    assert "<OperatorAccess" in shell
    assert '<aside className="sidebar">' not in app
    assert "<OperatorAccess" not in app


def test_standard_printer_card_is_feature_owned_and_vendor_neutral() -> None:
    root = Path(__file__).resolve().parents[3]
    app = (root / "frontend/src/FoxForgeApp.tsx").read_text(encoding="utf-8")
    card = (root / "frontend/src/features/printers/PrinterCard.tsx").read_text(encoding="utf-8")

    assert "function PrinterCard(" not in app
    assert "export function PrinterCard" in card
    assert "queueCount" in card
    assert "model ==" not in card
    assert "model ===" not in card
