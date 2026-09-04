# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from aiohttp import web

from foxforge.adapters.bambu import create_bambu_lan_adapter
from foxforge.adapters.moonraker import create_moonraker_http_adapter
from foxforge.api.v1 import BearerCommandSecurity, TrustedBrowserCommandSessions, create_api_v1_app
from foxforge.api.v1.command_audit import install_command_audit
from foxforge.api.v1.inventory_commands import register_inventory_command_routes
from foxforge.api.v1.queue_commands import register_queue_command_routes
from foxforge.application.artifacts import ArtifactStore
from foxforge.application.commands import CommandAuditStore, CommandIdempotencyStore
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InventoryService
from foxforge.application.queue import QueueService
from foxforge.domain.printers import ConnectionState, PrinterAdapterError
from foxforge.infrastructure.artifacts import FilesystemArtifactStore
from foxforge.infrastructure.commands import SQLiteCommandAuditStore, SQLiteCommandIdempotencyStore
from foxforge.infrastructure.inventory import SQLiteInventoryStore
from foxforge.infrastructure.printers import AdapterRegistry
from foxforge.infrastructure.queue import SQLiteQueueStore

from .config import load_runtime_config
from .printer_manager import RuntimePrinterManager

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    data_dir: Path
    config_path: Path
    static_dir: Path | None = None
    reconnect_seconds: float = 15.0
    command_token: str | None = None
    trusted_browser_sessions: bool = False

    def __post_init__(self) -> None:
        if self.reconnect_seconds <= 0:
            raise ValueError("reconnect_seconds must be positive")


@dataclass(slots=True)
class RuntimeComposition:
    fleet: FleetService
    queue: QueueService
    inventory: InventoryService
    artifacts: ArtifactStore
    command_idempotency: CommandIdempotencyStore
    command_audit: CommandAuditStore
    printer_manager: RuntimePrinterManager


_RUNTIME_KEY = web.AppKey("foxforge_runtime", RuntimeComposition)
_SUPERVISOR_KEY = web.AppKey("foxforge_connection_supervisor", asyncio.Task[None])


def create_runtime_app(settings: RuntimeSettings) -> web.Application:
    """Create the single-process FoxForge web runtime.

    Printer network reachability is deliberately not a startup prerequisite.
    Persisted printers are composed at startup; new printers can then be added,
    updated, tested, removed and reconnected through the live application API
    without restarting the server.
    """
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    config = load_runtime_config(settings.config_path)

    registry = AdapterRegistry()
    registry.register("bambu", create_bambu_lan_adapter)
    registry.register("moonraker", create_moonraker_http_adapter)

    adapters = tuple(registry.create(printer.identity, printer.settings) for printer in config.printers)
    fleet = FleetService(adapters)

    database_path = settings.data_dir / "foxforge.sqlite3"
    queue = QueueService(fleet, SQLiteQueueStore(database_path))
    inventory = InventoryService(SQLiteInventoryStore(database_path))
    artifacts = FilesystemArtifactStore(settings.data_dir / "artifacts")
    command_idempotency = SQLiteCommandIdempotencyStore(database_path)
    command_audit = SQLiteCommandAuditStore(database_path)
    browser_sessions = TrustedBrowserCommandSessions(enabled=settings.trusted_browser_sessions)
    command_security = BearerCommandSecurity(settings.command_token, browser_sessions=browser_sessions)
    printer_manager = RuntimePrinterManager(
        fleet=fleet,
        registry=registry,
        config_path=settings.config_path,
        config=config,
    )

    app = create_api_v1_app(
        fleet=fleet,
        queue=queue,
        inventory=inventory,
        command_security=command_security,
        command_idempotency=command_idempotency,
        printer_management=printer_manager,
    )
    register_inventory_command_routes(app, inventory=inventory, fleet=fleet)
    register_queue_command_routes(app, queue=queue, fleet=fleet, artifacts=artifacts)
    install_command_audit(app, security=command_security, store=command_audit)
    app[_RUNTIME_KEY] = RuntimeComposition(
        fleet=fleet,
        queue=queue,
        inventory=inventory,
        artifacts=artifacts,
        command_idempotency=command_idempotency,
        command_audit=command_audit,
        printer_manager=printer_manager,
    )
    app.on_startup.append(lambda runtime_app: _start_runtime(runtime_app, settings.reconnect_seconds))
    app.on_cleanup.append(_stop_runtime)
    _mount_frontend(app, settings.static_dir)
    return app


async def _start_runtime(app: web.Application, reconnect_seconds: float) -> None:
    runtime = app[_RUNTIME_KEY]
    await runtime.queue.start()
    app[_SUPERVISOR_KEY] = asyncio.create_task(
        _connection_supervisor(runtime.fleet, reconnect_seconds),
        name="foxforge-printer-connection-supervisor",
    )


async def _stop_runtime(app: web.Application) -> None:
    supervisor = app.get(_SUPERVISOR_KEY)
    if supervisor is not None:
        supervisor.cancel()
        with suppress(asyncio.CancelledError):
            await supervisor

    runtime = app[_RUNTIME_KEY]
    await runtime.queue.aclose()
    try:
        await runtime.fleet.aclose()
    except PrinterAdapterError:
        _LOG.exception("printer disconnect failed during FoxForge shutdown")


async def _connection_supervisor(fleet: FleetService, reconnect_seconds: float) -> None:
    while True:
        for printer_id in fleet.printer_ids:
            if fleet.snapshot(printer_id).connection != ConnectionState.DISCONNECTED:
                continue
            try:
                await fleet.connect(printer_id)
            except PrinterAdapterError as error:
                _LOG.warning(
                    "printer %s remains offline: %s (%s)",
                    printer_id,
                    error.message,
                    error.code.value,
                )
            except Exception:
                _LOG.exception("unexpected connection failure for printer %s", printer_id)
        await asyncio.sleep(reconnect_seconds)


def _mount_frontend(app: web.Application, static_dir: Path | None) -> None:
    if static_dir is None or not (static_dir / "index.html").is_file():

        async def runtime_info(_: web.Request) -> web.Response:
            return web.json_response(
                {
                    "name": "FoxForge",
                    "status": "api-only",
                    "message": "Frontend build is not installed in this runtime.",
                }
            )

        app.router.add_get("/", runtime_info)
        return

    assets = static_dir / "assets"
    if assets.is_dir():
        app.router.add_static("/assets/", assets, show_index=False)

    async def spa(request: web.Request) -> web.StreamResponse:
        if request.path.startswith("/api/"):
            return web.json_response({"error": "not_found"}, status=404)
        return web.FileResponse(static_dir / "index.html")

    app.router.add_get("/{tail:.*}", spa)
