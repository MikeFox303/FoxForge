# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import ast
from pathlib import Path


def test_printer_domain_has_no_vendor_adapter_imports() -> None:
    domain_root = Path("src/foxforge/domain/printers")
    forbidden = ("foxforge.adapters", "bambu", "moonraker")
    violations: list[str] = []

    for path in domain_root.rglob("*.py"):
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

    assert violations == []
