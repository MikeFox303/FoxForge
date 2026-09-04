# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from typing import Protocol


class SecretStore(Protocol):
    """Application-facing secret persistence port.

    Printer/domain code never depends on a concrete secret backend. Runtime
    composition may use a file-backed implementation today and replace it with
    container/external secret providers later without changing adapter contracts.
    """

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...

    def delete(self, key: str) -> None: ...
