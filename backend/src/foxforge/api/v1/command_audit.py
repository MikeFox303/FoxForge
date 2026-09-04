# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from aiohttp import web

from foxforge.application.commands import (
    CommandAuditOutcome,
    CommandAuditRecord,
    CommandAuditStore,
    command_idempotency_key_digest,
)

from .http import _REQUEST_ID_KEY, command_error
from .security import (
    BearerCommandSecurity,
    CommandAuthenticationError,
    CommandPrincipal,
    CommandSecurityDisabledError,
)

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _CommandRoute:
    method: str
    pattern: re.Pattern[str]
    action: str
    target_group: str | None = None


_COMMAND_ROUTES: Final = (
    _CommandRoute("POST", re.compile(r"^/api/v1/printers/test-connection$"), "printer.test_connection"),
    _CommandRoute("POST", re.compile(r"^/api/v1/printers$"), "printer.add"),
    _CommandRoute("PUT", re.compile(r"^/api/v1/printers/(?P<printer_id>[^/]+)$"), "printer.update", "printer_id"),
    _CommandRoute(
        "DELETE",
        re.compile(r"^/api/v1/printers/(?P<printer_id>[^/]+)$"),
        "printer.remove",
        "printer_id",
    ),
    _CommandRoute(
        "POST",
        re.compile(r"^/api/v1/printers/(?P<printer_id>[^/]+)/reconnect$"),
        "printer.reconnect",
        "printer_id",
    ),
    _CommandRoute(
        "POST",
        re.compile(r"^/api/v1/printers/(?P<printer_id>[^/]+)/job-control$"),
        "printer.job_control",
        "printer_id",
    ),
    _CommandRoute("POST", re.compile(r"^/api/v1/inventory/spools$"), "inventory.spool.add"),
    _CommandRoute(
        "POST",
        re.compile(r"^/api/v1/inventory/spools/(?P<spool_id>[^/]+)/correct-remaining$"),
        "inventory.spool.correct",
        "spool_id",
    ),
    _CommandRoute(
        "PATCH",
        re.compile(r"^/api/v1/inventory/spools/(?P<spool_id>[^/]+)/empty-spool-mass$"),
        "inventory.spool.empty_mass",
        "spool_id",
    ),
    _CommandRoute(
        "PUT",
        re.compile(r"^/api/v1/inventory/spools/(?P<spool_id>[^/]+)/assignment$"),
        "inventory.spool.move",
        "spool_id",
    ),
    _CommandRoute(
        "DELETE",
        re.compile(r"^/api/v1/inventory/spools/(?P<spool_id>[^/]+)/assignment$"),
        "inventory.spool.unassign",
        "spool_id",
    ),
    _CommandRoute(
        "POST",
        re.compile(r"^/api/v1/inventory/spools/(?P<spool_id>[^/]+)/archive$"),
        "inventory.spool.archive",
        "spool_id",
    ),
    _CommandRoute("POST", re.compile(r"^/api/v1/artifacts$"), "artifact.stage"),
    _CommandRoute("POST", re.compile(r"^/api/v1/queue$"), "queue.enqueue"),
    _CommandRoute(
        "POST",
        re.compile(r"^/api/v1/queue/(?P<queue_id>[^/]+)/dispatch$"),
        "queue.dispatch",
        "queue_id",
    ),
    _CommandRoute(
        "POST",
        re.compile(r"^/api/v1/queue/(?P<queue_id>[^/]+)/reconcile$"),
        "queue.reconcile",
        "queue_id",
    ),
)


def install_command_audit(
    app: web.Application,
    *,
    security: BearerCommandSecurity,
    store: CommandAuditStore,
) -> None:
    """Install fail-closed pre-side-effect audit for all FoxForge command routes."""

    @web.middleware
    async def command_audit(request: web.Request, handler):
        route = _match_command_route(request.method, request.path)
        if route is None:
            return await handler(request)

        target_ref = _route_target(route, request.path)
        principal = _authenticate_for_audit(security, request.headers.get("Authorization"))
        accepted_recorded = False
        if principal is not None:
            try:
                _append(
                    store,
                    request,
                    route,
                    CommandAuditOutcome.ACCEPTED,
                    principal=principal,
                    target_ref=target_ref,
                )
                accepted_recorded = True
            except Exception:
                _LOG.exception("command audit preflight failed for %s", route.action)
                return command_error(
                    request,
                    status=503,
                    code="audit_unavailable",
                    message="Command audit persistence is unavailable; the command was not executed.",
                    retryable=True,
                )

        try:
            response = await handler(request)
        except Exception:
            try:
                _append(
                    store,
                    request,
                    route,
                    CommandAuditOutcome.FAILED,
                    principal=principal,
                    target_ref=target_ref,
                    error_code="internal_error",
                )
            except Exception:
                _LOG.exception("command audit terminal write failed for %s", route.action)
            raise

        error_code = _response_error_code(response)
        outcome = _outcome_for_status(response.status)
        if principal is None and outcome != CommandAuditOutcome.DENIED:
            outcome = CommandAuditOutcome.DENIED

        if accepted_recorded or outcome == CommandAuditOutcome.DENIED:
            try:
                _append(
                    store,
                    request,
                    route,
                    outcome,
                    principal=principal,
                    target_ref=target_ref or _response_target(response),
                    error_code=error_code,
                )
            except Exception:
                _LOG.exception("command audit terminal write failed for %s", route.action)
        return response

    app.middlewares.append(command_audit)


def _authenticate_for_audit(
    security: BearerCommandSecurity,
    authorization_header: str | None,
) -> CommandPrincipal | None:
    try:
        return security.authenticate(authorization_header)
    except (CommandAuthenticationError, CommandSecurityDisabledError):
        return None


def _append(
    store: CommandAuditStore,
    request: web.Request,
    route: _CommandRoute,
    outcome: CommandAuditOutcome,
    *,
    principal: CommandPrincipal | None,
    target_ref: str | None,
    error_code: str | None = None,
) -> None:
    store.append(
        CommandAuditRecord(
            request_id=request[_REQUEST_ID_KEY],
            principal_id=None if principal is None else principal.principal_id,
            action=route.action,
            target_ref=target_ref,
            idempotency_key_digest=command_idempotency_key_digest(request.headers.get("Idempotency-Key")),
            outcome=outcome,
            error_code=error_code,
            occurred_at=datetime.now(UTC),
        )
    )


def _match_command_route(method: str, path: str) -> _CommandRoute | None:
    normalized_method = method.upper()
    for route in _COMMAND_ROUTES:
        if route.method == normalized_method and route.pattern.fullmatch(path):
            return route
    return None


def _route_target(route: _CommandRoute, path: str) -> str | None:
    if route.target_group is None:
        return None
    matched = route.pattern.fullmatch(path)
    if matched is None:
        return None
    return matched.group(route.target_group)


def _outcome_for_status(status: int) -> CommandAuditOutcome:
    if 200 <= status < 300:
        return CommandAuditOutcome.COMPLETED
    if status in {401, 403, 503}:
        return CommandAuditOutcome.DENIED
    if status == 409:
        return CommandAuditOutcome.CONFLICT
    return CommandAuditOutcome.FAILED


def _response_error_code(response: web.StreamResponse) -> str | None:
    if not isinstance(response, web.Response) or response.body is None:
        return None
    try:
        payload = json.loads(response.body.decode(response.charset or "utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return code if isinstance(code, str) and code else None


def _response_target(response: web.StreamResponse) -> str | None:
    if not isinstance(response, web.Response) or response.body is None:
        return None
    try:
        payload = json.loads(response.body.decode(response.charset or "utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    for field_name in ("queueId", "artifactId", "spoolId", "printerId"):
        value = payload.get(field_name)
        if isinstance(value, str) and value:
            return value
    configuration = payload.get("configuration")
    if isinstance(configuration, dict):
        value = configuration.get("printerId")
        if isinstance(value, str) and value:
            return value
    return None
