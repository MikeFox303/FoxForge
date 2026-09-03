# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PrinterErrorCode(StrEnum):
    CONNECTION_UNAVAILABLE = "connection_unavailable"
    AUTHENTICATION_FAILED = "authentication_failed"
    TIMEOUT = "timeout"
    BUSY = "busy"
    NOT_READY = "not_ready"
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED = "unsupported"
    CONFLICT = "conflict"
    REMOTE_REJECTED = "remote_rejected"
    INDETERMINATE = "indeterminate"
    INTERNAL_ADAPTER_ERROR = "internal_adapter_error"


@dataclass(eq=False)
class PrinterAdapterError(Exception):
    code: PrinterErrorCode
    message: str
    retryable: bool
    vendor_code: str | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)
