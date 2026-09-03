# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Protocol

from .native import MoonrakerNativeDispatchResult, MoonrakerNativePrintRequest, MoonrakerNativeState


class MoonrakerTransportErrorKind(StrEnum):
    UNAVAILABLE = "unavailable"
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    BUSY = "busy"
    REJECTED = "rejected"
    INDETERMINATE = "indeterminate"
    INTERNAL = "internal"


class MoonrakerTransportError(RuntimeError):
    def __init__(
        self,
        kind: MoonrakerTransportErrorKind,
        message: str,
        *,
        vendor_code: str | None = None,
    ) -> None:
        self.kind = kind
        self.message = message
        self.vendor_code = vendor_code
        super().__init__(message)


class MoonrakerTransport(Protocol):
    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    def snapshot(self) -> MoonrakerNativeState: ...

    def events(self) -> AsyncIterator[MoonrakerNativeState]: ...

    async def submit_print(self, request: MoonrakerNativePrintRequest) -> MoonrakerNativeDispatchResult: ...
