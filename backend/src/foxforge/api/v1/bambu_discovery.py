# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aiohttp import web

from foxforge.adapters.bambu import BambuDiscoveryCandidate, scan_bambu_subnet

from .http import add_command_route, command_error
from .security import CommandPermission

BambuSubnetScanner = Callable[[str], Awaitable[tuple[BambuDiscoveryCandidate, ...]]]


def register_bambu_discovery_routes(
    app: web.Application,
    *,
    scanner: BambuSubnetScanner | None = None,
) -> None:
    """Register authenticated Bambu discovery that returns candidates only.

    Network scanning is an operator action and is therefore guarded by the same
    printer-configuration permission used by Add Printer. Discovery never
    persists configuration and never receives the Bambu access code.
    """

    scan = scanner or _scan_default

    async def discover(request: web.Request) -> web.Response:
        if request.content_type != "application/json":
            return command_error(
                request,
                status=415,
                code="unsupported_media_type",
                message="Bambu discovery requires application/json.",
            )
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            unknown = set(payload) - {"subnet"}
            if unknown:
                raise ValueError(f"unsupported discovery fields: {', '.join(sorted(unknown))}")
            subnet = payload.get("subnet")
            if not isinstance(subnet, str) or not subnet.strip():
                raise ValueError("subnet must be a non-empty CIDR string")
            candidates = await scan(subnet.strip())
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        return web.json_response(
            {
                "apiVersion": "1",
                "candidates": [_candidate_model(candidate) for candidate in candidates],
            }
        )

    add_command_route(
        app,
        "POST",
        "/api/v1/printers/discovery/bambu",
        CommandPermission.PRINTER_CONFIG,
        discover,
    )


async def _scan_default(subnet: str) -> tuple[BambuDiscoveryCandidate, ...]:
    return await scan_bambu_subnet(subnet)


def _candidate_model(candidate: BambuDiscoveryCandidate) -> dict[str, object]:
    return {
        "host": candidate.host,
        "serialNumber": candidate.serial_number,
        "displayName": candidate.display_name,
        "model": candidate.model,
        "services": {
            "mqttPort": candidate.mqtt_port,
            "ftpsPort": candidate.ftps_port,
        },
    }
