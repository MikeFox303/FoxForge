# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Composition-layer HTTP routes for vendor-specific Bambu LAN discovery."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aiohttp import web

from foxforge.adapters.bambu import BambuDiscoveryCandidate, scan_bambu_subnet
from foxforge.api.v1.http import add_authenticated_route, add_command_route, command_error
from foxforge.api.v1.security import CommandPermission

from .local_networks import suggested_private_discovery_subnets

BambuSubnetScanner = Callable[[str], Awaitable[tuple[BambuDiscoveryCandidate, ...]]]
SubnetSuggester = Callable[[], tuple[str, ...]]


def register_bambu_discovery_routes(
    app: web.Application,
    *,
    scanner: BambuSubnetScanner | None = None,
    subnet_suggester: SubnetSuggester | None = None,
) -> None:
    """Register operator-only Bambu discovery and bounded subnet hints."""

    scan = scanner or _scan_default
    suggest_subnets = subnet_suggester or suggested_private_discovery_subnets

    async def suggestions(request: web.Request) -> web.Response:
        try:
            subnets = suggest_subnets()
        except (OSError, ValueError, TypeError):
            subnets = ()
        return web.json_response(
            {
                "apiVersion": "1",
                "subnets": list(subnets),
            }
        )

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

    add_authenticated_route(
        app,
        "GET",
        "/api/v1/printers/discovery/bambu/subnets",
        CommandPermission.PRINTER_CONFIG,
        suggestions,
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
