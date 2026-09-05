# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from uuid import UUID

from aiohttp import web

from foxforge.application.inventory import InventoryService, SpoolNotFoundError
from foxforge.domain.inventory import SpoolAdjustment

from .http import command_error


def register_inventory_read_routes(app: web.Application, *, inventory: InventoryService) -> None:
    """Register bounded public inventory reads that do not expose internal idempotency keys."""

    async def spool_history(request: web.Request) -> web.Response:
        try:
            spool_id = UUID(request.match_info["spool_id"])
            adjustments = inventory.adjustments(spool_id)
        except (ValueError, SpoolNotFoundError):
            return command_error(
                request,
                status=404,
                code="spool_not_found",
                message="Spool was not found.",
            )

        ordered = sorted(adjustments, key=lambda item: (item.created_at, str(item.adjustment_id)), reverse=True)
        return web.json_response(
            {
                "apiVersion": "1",
                "spoolId": str(spool_id),
                "adjustments": [_adjustment(item) for item in ordered],
            }
        )

    app.router.add_get("/api/v1/inventory/spools/{spool_id}/history", spool_history)


def _adjustment(adjustment: SpoolAdjustment) -> dict[str, object]:
    return {
        "adjustmentId": str(adjustment.adjustment_id),
        "kind": adjustment.kind.value,
        "deltaFilamentMassG": str(adjustment.delta_filament_mass_g),
        "createdAt": adjustment.created_at.isoformat().replace("+00:00", "Z"),
        "note": adjustment.note,
    }
