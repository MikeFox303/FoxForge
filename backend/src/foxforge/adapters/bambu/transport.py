# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Transport boundary consumed by the FoxForge Bambu adapter.

Concrete MQTT/FTP/X2D implementations live below this protocol. This module is
new FoxForge code and deliberately exposes Bambu-native semantics only inside
the Bambu adapter package.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .native import (
    BambuNativeDispatchResult,
    BambuNativeJobControlAction,
    BambuNativeJobControlResult,
    BambuNativePrintRequest,
    BambuNativeState,
)


class BambuTransportErrorKind(StrEnum):
    UNAVAILABLE = "unavailable"
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    BUSY = "busy"
    REJECTED = "rejected"
    INDETERMINATE = "indeterminate"
    INTERNAL = "internal"


@dataclass(eq=False)
class BambuTransportError(Exception):
    kind: BambuTransportErrorKind
    message: str
    vendor_code: str | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


class BambuTransport(Protocol):
    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    def snapshot(self) -> BambuNativeState: ...

    def events(self) -> AsyncIterator[BambuNativeState]: ...

    async def submit_print(self, request: BambuNativePrintRequest) -> BambuNativeDispatchResult: ...

    async def control_print(self, action: BambuNativeJobControlAction) -> BambuNativeJobControlResult: ...
