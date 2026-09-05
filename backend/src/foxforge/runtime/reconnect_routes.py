# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from datetime import UTC, datetime

from aiohttp import web

from .reconnect import ReconnectDiagnostics, ReconnectPrinterStatus


def register_reconnect_diagnostic_routes(app: web.Application, diagnostics: ReconnectDiagnostics) -> None:
    """Expose secret-safe reconnect context for the operator-facing diagnostics UI."""

    async def reconnect_diagnostics(_: web.Request) -> web.Response:
        return web.json_response(
            {
                "apiVersion": "1",
                "printers": [_status_model(status) for status in diagnostics.statuses()],
            }
        )

    app.router.add_get("/api/v1/diagnostics/reconnect", reconnect_diagnostics)


def _status_model(status: ReconnectPrinterStatus) -> dict[str, object]:
    return {
        "printerId": status.printer_id,
        "consecutiveFailures": status.consecutive_failures,
        "lastAttemptAt": _datetime(status.last_attempt_at),
        "lastFailureAt": _datetime(status.last_failure_at),
        "lastErrorCode": None if status.last_error_code is None else status.last_error_code.value,
        "lastErrorRetryable": status.last_error_retryable,
        "nextRetryAt": _datetime(status.next_retry_at),
        "recoveredAt": _datetime(status.recovered_at),
    }


def _datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
