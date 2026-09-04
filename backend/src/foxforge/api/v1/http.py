# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from uuid import uuid4

from aiohttp import web

from foxforge.application.commands import CommandIdempotencyStore
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InventoryService
from foxforge.application.queue import QueueService

from .read_models import API_VERSION, fleet_read_model, inventory_read_model, queue_read_model
from .security import (
    BearerCommandSecurity,
    CommandAuthenticationError,
    CommandPermission,
    CommandPrincipal,
    CommandSecurityDisabledError,
)

_JSON_HANDLER = Callable[[web.Request], Awaitable[web.StreamResponse]]
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

_REQUEST_ID_KEY = web.AppKey("foxforge_request_id", str)
_COMMAND_SECURITY_KEY = web.AppKey("foxforge_command_security", BearerCommandSecurity)
_COMMAND_PRINCIPAL_KEY = web.AppKey("foxforge_command_principal", CommandPrincipal)
_COMMAND_IDEMPOTENCY_KEY = web.AppKey("foxforge_command_idempotency", CommandIdempotencyStore)


def create_api_v1_app(
    *,
    fleet: FleetService,
    queue: QueueService,
    inventory: InventoryService,
    command_security: BearerCommandSecurity | None = None,
    command_idempotency: CommandIdempotencyStore | None = None,
) -> web.Application:
    """Create the FoxForge HTTP API v1 application.

    Existing read endpoints remain compatible with the alpha.2 contract. ADR
    0004 command security is installed here so later mutation routes can be
    added only through the explicit guarded-route helper.
    """

    app = web.Application(middlewares=[_request_context, _response_headers])
    app[_COMMAND_SECURITY_KEY] = command_security or BearerCommandSecurity(None)
    if command_idempotency is not None:
        app[_COMMAND_IDEMPOTENCY_KEY] = command_idempotency

    async def healthz(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "apiVersion": API_VERSION})

    async def fleet_snapshot(_: web.Request) -> web.Response:
        return web.json_response(fleet_read_model(fleet))

    async def queue_snapshot(_: web.Request) -> web.Response:
        return web.json_response(queue_read_model(queue))

    async def inventory_spools(_: web.Request) -> web.Response:
        return web.json_response(inventory_read_model(inventory))

    _add_get(app, "/healthz", healthz)
    _add_get(app, "/api/v1/fleet", fleet_snapshot)
    _add_get(app, "/api/v1/queue", queue_snapshot)
    _add_get(app, "/api/v1/inventory/spools", inventory_spools)
    return app


def add_command_route(
    app: web.Application,
    method: str,
    path: str,
    permission: CommandPermission,
    handler: _JSON_HANDLER,
) -> None:
    """Register one state-changing route behind ADR 0004 authentication."""

    normalized_method = method.upper()
    if normalized_method in {"GET", "HEAD", "OPTIONS"}:
        raise ValueError("command routes must use a state-changing HTTP method")

    async def guarded(request: web.Request) -> web.StreamResponse:
        security = request.app[_COMMAND_SECURITY_KEY]
        try:
            principal = security.authenticate(request.headers.get("Authorization"))
        except CommandSecurityDisabledError:
            return _command_error(
                request,
                status=503,
                code="command_api_disabled",
                message="Command API is not enabled for this FoxForge runtime.",
            )
        except CommandAuthenticationError:
            response = _command_error(
                request,
                status=401,
                code="unauthorized",
                message="Valid command credentials are required.",
            )
            response.headers["WWW-Authenticate"] = "Bearer"
            return response

        if not principal.allows(permission):
            return _command_error(
                request,
                status=403,
                code="forbidden",
                message="The authenticated principal is not permitted to perform this command.",
            )

        request[_COMMAND_PRINCIPAL_KEY] = principal
        return await handler(request)

    app.router.add_route(normalized_method, path, guarded)


def command_principal(request: web.Request) -> CommandPrincipal:
    """Return the authenticated principal inside an ADR 0004 command handler."""

    principal = request.get(_COMMAND_PRINCIPAL_KEY)
    if principal is None:
        raise RuntimeError("command principal is unavailable outside an authenticated command handler")
    return principal


def command_idempotency_store(request: web.Request) -> CommandIdempotencyStore:
    """Return the configured durable command-idempotency store."""

    store = request.app.get(_COMMAND_IDEMPOTENCY_KEY)
    if store is None:
        raise RuntimeError("durable command idempotency store is not configured")
    return store


@web.middleware
async def _request_context(request: web.Request, handler: _JSON_HANDLER) -> web.StreamResponse:
    candidate = request.headers.get("X-Request-Id")
    request[_REQUEST_ID_KEY] = candidate if candidate is not None and _REQUEST_ID_RE.fullmatch(candidate) else str(uuid4())
    return await handler(request)


@web.middleware
async def _response_headers(request: web.Request, handler: _JSON_HANDLER) -> web.StreamResponse:
    response = await handler(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-FoxForge-Api-Version"] = API_VERSION
    response.headers["X-Request-Id"] = request[_REQUEST_ID_KEY]
    return response


def _command_error(
    request: web.Request,
    *,
    status: int,
    code: str,
    message: str,
    retryable: bool = False,
) -> web.Response:
    return web.json_response(
        {
            "error": {
                "code": code,
                "message": message,
                "requestId": request[_REQUEST_ID_KEY],
                "retryable": retryable,
            }
        },
        status=status,
    )


def _add_get(app: web.Application, path: str, handler: _JSON_HANDLER) -> None:
    app.router.add_get(path, handler)
