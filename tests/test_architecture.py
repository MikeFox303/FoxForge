# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import ast
from pathlib import Path


def _forbidden_imports(root: Path, forbidden: tuple[str, ...]) -> list[str]:
    violations: list[str] = []

    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if any(token in name.lower() for token in forbidden):
                    violations.append(f"{path}: {name}")

    return violations


def test_printer_domain_has_no_vendor_adapter_imports() -> None:
    violations = _forbidden_imports(
        Path("src/foxforge/domain/printers"),
        ("foxforge.adapters", "bambu", "moonraker"),
    )
    assert violations == []


def test_application_layer_has_no_vendor_adapter_imports() -> None:
    violations = _forbidden_imports(
        Path("src/foxforge/application"),
        ("foxforge.adapters", "bambu", "moonraker"),
    )
    assert violations == []


def test_adapter_registry_has_no_vendor_imports() -> None:
    violations = _forbidden_imports(
        Path("src/foxforge/infrastructure/printers"),
        ("foxforge.adapters", "bambu", "moonraker"),
    )
    assert violations == []


def test_queue_storage_has_no_vendor_imports() -> None:
    violations = _forbidden_imports(
        Path("src/foxforge/infrastructure/queue"),
        ("foxforge.adapters", "bambu", "moonraker"),
    )
    assert violations == []
