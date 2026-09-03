# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, TypeVar

from .events import PrinterEvent
from .models import PrinterIdentity, PrinterSnapshot

C = TypeVar("C")


class CapabilityResolver(Protocol):
    def capability(self, capability_type: type[C]) -> C | None: ...


class PrinterAdapter(CapabilityResolver, Protocol):
    @property
    def identity(self) -> PrinterIdentity: ...

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    def snapshot(self) -> PrinterSnapshot: ...

    def events(self) -> AsyncIterator[PrinterEvent]: ...
