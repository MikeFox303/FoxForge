# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from aiohttp import web

from foxforge.application.commands import (
    CommandIdempotencyConflictError,
    CommandIdempotencyRecord,
    CommandIdempotencyState,
    command_request_fingerprint,
)
from foxforge.application.fleet import FleetPrinterNotFoundError, FleetService
from foxforge.application.inventory import (
    ArchivedSpoolError,
    InventoryBalanceError,
    InventoryIdempotencyConflictError,
    InventoryService,
    InventoryStoreConflictError,
    SpoolAssignmentConflictError,
    SpoolNotFoundError,
)
from foxforge.domain.inventory import Spool, SpoolColor
from foxforge.domain.printers.capabilities import MaterialSystemCapability

from .http import add_command_route, command_error, command_idempotency_store, command_principal
from .security import CommandPermission


def register_inventory_command_routes(
    app: web.Application,
    *,
    inventory: InventoryService,
    fleet: FleetService,
) -> None:
    """Register authenticated restart-safe inventory write endpoints."""

    async def add_spool(request: web.Request) -> web.Response:
        try:
            payload = await _json_object(request)
            spool_id = _uuid(payload.get("spoolId"), "spoolId")
            reservation = _reserve(request, "inventory.spool.add", payload)
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            replay = _reconcile_created_spool(inventory, spool_id, payload)
            if replay is None:
                return command_error(
                    request,
                    status=409,
                    code="reconciliation_required",
                    message="The previous add-spool outcome cannot be confirmed safely.",
                )
            _complete(request, "inventory.spool.add", payload, result_ref=str(spool_id))
            return web.json_response(_spool_result(inventory, replay, replayed=True))

        try:
            spool = inventory.add_spool(
                spool_id=spool_id,
                material_family=_required_text(payload, "materialFamily"),
                initial_filament_mass_g=_positive_decimal(payload.get("initialFilamentMassG"), "initialFilamentMassG"),
                manufacturer=_optional_text(payload.get("manufacturer")),
                product_name=_optional_text(payload.get("productName")),
                color=_color(payload.get("rgbaHex")),
                empty_spool_mass_g=_optional_nonnegative_decimal(payload.get("emptySpoolMassG"), "emptySpoolMassG"),
                purchase_date=_optional_date(payload.get("purchaseDate")),
            )
        except InventoryStoreConflictError:
            spool = _reconcile_created_spool(inventory, spool_id, payload)
            if spool is None:
                return command_error(request, status=409, code="spool_exists", message="spoolId is already in use")
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        _complete(request, "inventory.spool.add", payload, result_ref=str(spool_id))
        return web.json_response(_spool_result(inventory, spool), status=201)

    async def correct_remaining(request: web.Request) -> web.Response:
        try:
            spool_id = _route_spool_id(request)
            payload = await _json_object(request)
            target = _nonnegative_decimal(payload.get("remainingFilamentMassG"), "remainingFilamentMassG")
            note = _optional_text(payload.get("note"))
            reservation = _reserve(request, "inventory.spool.correct", payload, route_identity=str(spool_id))
            ledger_key = _idempotency_key(request)
            current = inventory.balance(spool_id).remaining_filament_mass_g
            if target == current:
                _complete(
                    request,
                    "inventory.spool.correct",
                    payload,
                    route_identity=str(spool_id),
                    result_ref=str(spool_id),
                )
                return web.json_response(_balance_result(inventory, spool_id, replayed=not reservation.created))
            adjustment = inventory.correct_by_delta(
                spool_id,
                target - current,
                idempotency_key=ledger_key,
                note=note,
            )
        except SpoolNotFoundError:
            return command_error(request, status=404, code="spool_not_found", message="Spool was not found.")
        except ArchivedSpoolError as error:
            return command_error(request, status=409, code="spool_archived", message=str(error))
        except InventoryBalanceError as error:
            return command_error(request, status=409, code="invalid_balance", message=str(error))
        except InventoryIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        _complete(
            request,
            "inventory.spool.correct",
            payload,
            route_identity=str(spool_id),
            result_ref=str(spool_id),
        )
        result = _balance_result(inventory, spool_id, replayed=not reservation.created)
        result["adjustmentId"] = str(adjustment.adjustment_id)
        result["deltaFilamentMassG"] = str(adjustment.delta_filament_mass_g)
        return web.json_response(result)

    async def set_empty_mass(request: web.Request) -> web.Response:
        try:
            spool_id = _route_spool_id(request)
            payload = await _json_object(request)
            value = _optional_nonnegative_decimal(payload.get("emptySpoolMassG"), "emptySpoolMassG")
            reservation = _reserve(request, "inventory.spool.empty_mass", payload, route_identity=str(spool_id))
            spool = inventory.set_empty_spool_mass(spool_id, value)
        except SpoolNotFoundError:
            return command_error(request, status=404, code="spool_not_found", message="Spool was not found.")
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        _complete(
            request,
            "inventory.spool.empty_mass",
            payload,
            route_identity=str(spool_id),
            result_ref=str(spool_id),
        )
        return web.json_response(_spool_result(inventory, spool, replayed=not reservation.created))

    async def move_spool(request: web.Request) -> web.Response:
        try:
            spool_id = _route_spool_id(request)
            payload = await _json_object(request)
            printer_id = _required_text(payload, "printerId")
            slot_id = _required_text(payload, "slotId")
            reservation = _reserve(request, "inventory.spool.move", payload, route_identity=str(spool_id))
            _validate_slot(fleet, printer_id, slot_id)
            assignment = inventory.move_spool(spool_id, printer_id, slot_id)
        except SpoolNotFoundError:
            return command_error(request, status=404, code="spool_not_found", message="Spool was not found.")
        except FleetPrinterNotFoundError:
            return command_error(request, status=404, code="printer_not_found", message="Printer was not found.")
        except ArchivedSpoolError as error:
            return command_error(request, status=409, code="spool_archived", message=str(error))
        except SpoolAssignmentConflictError as error:
            return command_error(request, status=409, code="assignment_conflict", message=str(error))
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        _complete(
            request,
            "inventory.spool.move",
            payload,
            route_identity=str(spool_id),
            result_ref=str(spool_id),
        )
        return web.json_response(
            {
                "spoolId": str(spool_id),
                "printerId": assignment.printer_id,
                "slotId": assignment.slot_id,
                "assignedAt": _datetime(assignment.assigned_at),
                "replayed": not reservation.created,
            }
        )

    async def unassign_spool(request: web.Request) -> web.Response:
        try:
            spool_id = _route_spool_id(request)
            payload: dict[str, object] = {}
            reservation = _reserve(request, "inventory.spool.unassign", payload, route_identity=str(spool_id))
            previous = inventory.unassign_spool(spool_id)
        except SpoolNotFoundError:
            return command_error(request, status=404, code="spool_not_found", message="Spool was not found.")
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        _complete(
            request,
            "inventory.spool.unassign",
            payload,
            route_identity=str(spool_id),
            result_ref=str(spool_id),
        )
        return web.json_response(
            {
                "spoolId": str(spool_id),
                "unassigned": True,
                "hadAssignment": previous is not None,
                "replayed": not reservation.created,
            }
        )

    async def archive_spool(request: web.Request) -> web.Response:
        try:
            spool_id = _route_spool_id(request)
            payload: dict[str, object] = {}
            reservation = _reserve(request, "inventory.spool.archive", payload, route_identity=str(spool_id))
            spool = inventory.archive_spool(spool_id)
        except SpoolNotFoundError:
            return command_error(request, status=404, code="spool_not_found", message="Spool was not found.")
        except SpoolAssignmentConflictError as error:
            return command_error(request, status=409, code="assignment_conflict", message=str(error))
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        _complete(
            request,
            "inventory.spool.archive",
            payload,
            route_identity=str(spool_id),
            result_ref=str(spool_id),
        )
        return web.json_response(_spool_result(inventory, spool, replayed=not reservation.created))

    add_command_route(app, "POST", "/api/v1/inventory/spools", CommandPermission.INVENTORY_WRITE, add_spool)
    add_command_route(
        app,
        "POST",
        "/api/v1/inventory/spools/{spool_id}/correct-remaining",
        CommandPermission.INVENTORY_WRITE,
        correct_remaining,
    )
    add_command_route(
        app,
        "PATCH",
        "/api/v1/inventory/spools/{spool_id}/empty-spool-mass",
        CommandPermission.INVENTORY_WRITE,
        set_empty_mass,
    )
    add_command_route(
        app,
        "PUT",
        "/api/v1/inventory/spools/{spool_id}/assignment",
        CommandPermission.INVENTORY_WRITE,
        move_spool,
    )
    add_command_route(
        app,
        "DELETE",
        "/api/v1/inventory/spools/{spool_id}/assignment",
        CommandPermission.INVENTORY_WRITE,
        unassign_spool,
    )
    add_command_route(
        app,
        "POST",
        "/api/v1/inventory/spools/{spool_id}/archive",
        CommandPermission.INVENTORY_WRITE,
        archive_spool,
    )


def _reserve(
    request: web.Request,
    operation: str,
    payload: object,
    *,
    route_identity: str | None = None,
):
    key = _idempotency_key(request)
    principal = command_principal(request)
    fingerprint_payload = {"routeIdentity": route_identity, "payload": payload}
    now = datetime.now(UTC)
    return command_idempotency_store(request).reserve(
        CommandIdempotencyRecord(
            principal_id=principal.principal_id,
            operation=operation,
            idempotency_key=key,
            request_fingerprint=command_request_fingerprint(fingerprint_payload),
            state=CommandIdempotencyState.STARTED,
            created_at=now,
            updated_at=now,
        )
    )


def _complete(
    request: web.Request,
    operation: str,
    payload: object,
    *,
    result_ref: str,
    route_identity: str | None = None,
) -> None:
    principal = command_principal(request)
    fingerprint_payload = {"routeIdentity": route_identity, "payload": payload}
    command_idempotency_store(request).complete(
        principal_id=principal.principal_id,
        operation=operation,
        idempotency_key=_idempotency_key(request),
        request_fingerprint=command_request_fingerprint(fingerprint_payload),
        outcome_code="completed",
        result_ref=result_ref,
    )


def _idempotency_key(request: web.Request) -> str:
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key:
        raise ValueError("Idempotency-Key header is required")
    return key


def _validate_slot(fleet: FleetService, printer_id: str, slot_id: str) -> None:
    fleet.snapshot(printer_id)
    material_system = fleet.capability(printer_id, MaterialSystemCapability)
    if material_system is None:
        raise ValueError("selected printer does not expose a material system")
    known_slots = {slot.slot_id for unit in material_system.snapshot().units for slot in unit.slots}
    if slot_id not in known_slots:
        raise ValueError("slotId is not reported by the selected printer")


def _reconcile_created_spool(
    inventory: InventoryService,
    spool_id: UUID,
    payload: dict[str, object],
) -> Spool | None:
    try:
        spool = inventory.get_spool(spool_id)
    except SpoolNotFoundError:
        return None
    return spool if _spool_matches(spool, payload) else None


def _spool_matches(spool: Spool, payload: dict[str, object]) -> bool:
    try:
        return (
            spool.spool_id == _uuid(payload.get("spoolId"), "spoolId")
            and spool.material_family == _required_text(payload, "materialFamily")
            and spool.initial_filament_mass_g
            == _positive_decimal(payload.get("initialFilamentMassG"), "initialFilamentMassG")
            and spool.manufacturer == _optional_text(payload.get("manufacturer"))
            and spool.product_name == _optional_text(payload.get("productName"))
            and spool.color == _color(payload.get("rgbaHex"))
            and spool.empty_spool_mass_g
            == _optional_nonnegative_decimal(payload.get("emptySpoolMassG"), "emptySpoolMassG")
            and spool.purchase_date == _optional_date(payload.get("purchaseDate"))
        )
    except (ValueError, TypeError):
        return False


def _spool_result(inventory: InventoryService, spool: Spool, *, replayed: bool = False) -> dict[str, object]:
    balance = inventory.balance(spool.spool_id)
    return {
        "spoolId": str(spool.spool_id),
        "remainingFilamentMassG": str(balance.remaining_filament_mass_g),
        "emptySpoolMassG": None if spool.empty_spool_mass_g is None else str(spool.empty_spool_mass_g),
        "archived": spool.archived,
        "replayed": replayed,
    }


def _balance_result(inventory: InventoryService, spool_id: UUID, *, replayed: bool) -> dict[str, object]:
    balance = inventory.balance(spool_id)
    return {
        "spoolId": str(spool_id),
        "remainingFilamentMassG": str(balance.remaining_filament_mass_g),
        "usedFilamentMassG": str(balance.used_filament_mass_g),
        "replayed": replayed,
    }


async def _json_object(request: web.Request) -> dict[str, object]:
    try:
        payload = await request.json()
    except Exception as error:
        raise ValueError("request body must be valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


def _route_spool_id(request: web.Request) -> UUID:
    return _uuid(request.match_info["spool_id"], "spoolId")


def _uuid(value: object, field_name: str) -> UUID:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a valid UUID") from error


def _required_text(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional text values must be strings or null")
    cleaned = value.strip()
    return cleaned or None


def _decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise ValueError(f"{field_name} must be a decimal-compatible value")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"{field_name} must be a decimal-compatible value") from error
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


def _positive_decimal(value: object, field_name: str) -> Decimal:
    result = _decimal(value, field_name)
    if result <= 0:
        raise ValueError(f"{field_name} must be positive")
    return result


def _nonnegative_decimal(value: object, field_name: str) -> Decimal:
    result = _decimal(value, field_name)
    if result < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return result


def _optional_nonnegative_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None or value == "":
        return None
    return _nonnegative_decimal(value, field_name)


def _color(value: object) -> SpoolColor | None:
    text = _optional_text(value)
    return None if text is None else SpoolColor(text.removeprefix("#"))


def _optional_date(value: object) -> date | None:
    text = _optional_text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise ValueError("purchaseDate must be YYYY-MM-DD") from error


def _datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
