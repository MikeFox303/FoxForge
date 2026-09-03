# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aiohttp import web

from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InventoryService
from foxforge.application.queue import QueueService

from .read_models import API_VERSION, fleet_read_model, inventory_read_model, queue_read_model

_JSON_HANDLER = Callable[[web.Request], Awaitable[web.StreamResponse]]


def create_api_v1_app(
    *,
    fleet: FleetService,
    queue: QueueService,
    inventory: InventoryService,
) -> web.Application:
    """Create the read-only FoxForge HTTP API v1 application.

    Phase 13 intentionally exposes observation/read models only. Printer control,
    queue mutations and inventory mutations remain behind application services
    until authentication, request validation and mutation error semantics are
    specified.
    """

    app = web.Application(middlewares=[_response_headers])

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


@web.middleware
async def _response_headers(request: web.Request, handler: _JSON_HANDLER) -> web.StreamResponse:
    response = await handler(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-FoxForge-Api-Version"] = API_VERSION
    return response


def _add_get(app: web.Application, path: str, handler: _JSON_HANDLER) -> None:
    app.router.add_get(path, handler)
