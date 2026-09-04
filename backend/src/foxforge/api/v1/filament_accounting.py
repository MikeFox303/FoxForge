# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from aiohttp import web

from foxforge.application.accounting import (
    FilamentAccountingError,
    FilamentAccountingService,
    FilamentAssignmentRequiredError,
    FilamentCapacityError,
    FilamentPlanConflictError,
    FilamentReconciliationRequiredError,
    FilamentReservation,
    FilamentReservationNotFoundError,
    MaterialEstimate,
)
from foxforge.application.commands import (
    CommandIdempotencyConflictError,
    CommandIdempotencyRecord,
    CommandIdempotencyState,
    command_request_fingerprint,
)
from foxforge.application.queue import QueueEntryNotFoundError, QueueEntryState, QueueService

from .http import add_command_route, command_error, command_idempotency_store, command_principal
from .security import CommandPermission


def register_filament_accounting_routes(
    app: web.Application,
    *,
    queue: QueueService,
    accounting: FilamentAccountingService,
) -> None:
    async def snapshot(_: web.Request) -> web.Response:
        reservations = accounting.reservations()
        spool_ids = sorted({reservation.spool_id for reservation in reservations}, key=str)
        return web.json_response(
            {
                "apiVersion": "1",
                "reservations": [_reservation(item) for item in reservations],
                "spools": [
                    {
                        "spoolId": str(spool_id),
                        "reservedMassG": str(accounting.reserved_mass(spool_id)),
                        "availableMassG": str(accounting.available_mass(spool_id)),
                    }
                    for spool_id in spool_ids
                ],
            }
        )

    async def plan(request: web.Request) -> web.Response:
        try:
            queue_id = _route_queue_id(request)
            entry = queue.get(queue_id)
            payload = await _json_object(request)
            _only_fields(payload, {"estimates"})
            estimates = _estimates(payload.get("estimates"))
            if not estimates:
                raise ValueError("estimates must contain at least one material estimate")
            if entry.receipt is not None or entry.state in {
                QueueEntryState.DISPATCHING,
                QueueEntryState.INDETERMINATE,
                QueueEntryState.ACCEPTED,
                QueueEntryState.PREPARING,
                QueueEntryState.PRINTING,
                QueueEntryState.PAUSED,
                QueueEntryState.COMPLETED,
                QueueEntryState.CANCELLED,
            }:
                raise FilamentPlanConflictError("filament plan must be created before confirmed print start")
            if not accounting.reservations_for_queue(queue_id):
                accounting.preview_plan(entry.printer_id, entry.request.material_bindings, estimates)
            reservation = _reserve(request, "filament.plan", payload, route_identity=str(queue_id))
        except QueueEntryNotFoundError:
            return command_error(request, status=404, code="queue_not_found", message="Queue entry was not found.")
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except FilamentAssignmentRequiredError as error:
            return command_error(request, status=409, code="filament_assignment_required", message=str(error))
        except FilamentCapacityError as error:
            return command_error(request, status=409, code="insufficient_filament", message=str(error))
        except (FilamentPlanConflictError, FilamentAccountingError) as error:
            return command_error(request, status=409, code="filament_plan_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            if reservation.record.state != CommandIdempotencyState.COMPLETED:
                return command_error(
                    request,
                    status=409,
                    code="reconciliation_required",
                    message="A previous filament-plan command with this idempotency key is unresolved.",
                )
            return web.json_response(_queue_accounting_result(accounting, queue_id, replayed=True))

        try:
            accounting.plan(entry, estimates)
        except FilamentAccountingError as error:
            return command_error(request, status=409, code="filament_plan_conflict", message=str(error))
        _complete(
            request,
            "filament.plan",
            payload,
            route_identity=str(queue_id),
            result_ref=str(queue_id),
            outcome_code="planned",
        )
        return web.json_response(_queue_accounting_result(accounting, queue_id), status=201)

    async def release(request: web.Request) -> web.Response:
        try:
            queue_id = _route_queue_id(request)
            entry = queue.get(queue_id)
            payload: dict[str, object] = {}
            reservation = _reserve(request, "filament.release", payload, route_identity=str(queue_id))
        except QueueEntryNotFoundError:
            return command_error(request, status=404, code="queue_not_found", message="Queue entry was not found.")
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            if reservation.record.state != CommandIdempotencyState.COMPLETED:
                return command_error(
                    request,
                    status=409,
                    code="reconciliation_required",
                    message="A previous filament-release command with this idempotency key is unresolved.",
                )
            return web.json_response(_queue_accounting_result(accounting, queue_id, replayed=True))

        try:
            accounting.release_unstarted(entry)
        except FilamentReconciliationRequiredError as error:
            return command_error(request, status=409, code="filament_reconciliation_required", message=str(error))
        _complete(
            request,
            "filament.release",
            payload,
            route_identity=str(queue_id),
            result_ref=str(queue_id),
            outcome_code="released",
        )
        return web.json_response(_queue_accounting_result(accounting, queue_id))

    async def reconcile(request: web.Request) -> web.Response:
        try:
            queue_id = _route_queue_id(request)
            queue.get(queue_id)
            payload = await _json_object(request)
            _only_fields(payload, {"materialIndex", "actualMassG", "note"})
            material_index = _material_index(payload.get("materialIndex"))
            actual_mass_g = _mass(payload.get("actualMassG"), field_name="actualMassG", allow_zero=True)
            note = _optional_text(payload.get("note"), field_name="note")
            reservation = _reserve(request, "filament.reconcile", payload, route_identity=str(queue_id))
        except QueueEntryNotFoundError:
            return command_error(request, status=404, code="queue_not_found", message="Queue entry was not found.")
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            if reservation.record.state != CommandIdempotencyState.COMPLETED:
                return command_error(
                    request,
                    status=409,
                    code="reconciliation_required",
                    message="A previous filament-reconciliation command with this key is unresolved.",
                )
            return web.json_response(_queue_accounting_result(accounting, queue_id, replayed=True))

        try:
            accounting.reconcile(
                queue_id,
                material_index,
                actual_mass_g=actual_mass_g,
                note=note,
            )
        except FilamentReservationNotFoundError:
            return command_error(
                request,
                status=404,
                code="filament_reservation_not_found",
                message="Filament reservation was not found.",
            )
        except FilamentReconciliationRequiredError as error:
            return command_error(request, status=409, code="filament_reconciliation_not_allowed", message=str(error))
        except FilamentCapacityError as error:
            return command_error(request, status=409, code="insufficient_filament", message=str(error))

        _complete(
            request,
            "filament.reconcile",
            payload,
            route_identity=str(queue_id),
            result_ref=f"{queue_id}:{material_index}",
            outcome_code="reconciled",
        )
        return web.json_response(_queue_accounting_result(accounting, queue_id))

    app.router.add_get("/api/v1/filament-accounting", snapshot)
    add_command_route(
        app,
        "POST",
        "/api/v1/queue/{queue_id}/filament-plan",
        CommandPermission.QUEUE_WRITE,
        plan,
    )
    add_command_route(
        app,
        "POST",
        "/api/v1/queue/{queue_id}/filament-release",
        CommandPermission.QUEUE_WRITE,
        release,
    )
    add_command_route(
        app,
        "POST",
        "/api/v1/queue/{queue_id}/filament-reconcile",
        CommandPermission.INVENTORY_WRITE,
        reconcile,
    )


def _queue_accounting_result(
    accounting: FilamentAccountingService,
    queue_id: UUID,
    *,
    replayed: bool = False,
) -> dict[str, object]:
    return {
        "apiVersion": "1",
        "queueId": str(queue_id),
        "reservations": [_reservation(item) for item in accounting.reservations_for_queue(queue_id)],
        "replayed": replayed,
    }


def _reservation(item: FilamentReservation) -> dict[str, object]:
    return {
        "queueId": str(item.queue_id),
        "materialIndex": item.material_index,
        "spoolId": str(item.spool_id),
        "printerId": item.printer_id,
        "slotId": item.slot_id,
        "estimatedMassG": str(item.estimated_mass_g),
        "actualMassG": None if item.actual_mass_g is None else str(item.actual_mass_g),
        "state": item.state.value,
        "createdAt": item.created_at.isoformat().replace("+00:00", "Z"),
        "updatedAt": item.updated_at.isoformat().replace("+00:00", "Z"),
        "note": item.note,
    }


def _estimates(value: object) -> tuple[MaterialEstimate, ...]:
    if not isinstance(value, list):
        raise ValueError("estimates must be an array")
    estimates: list[MaterialEstimate] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"estimates[{index}] must be an object")
        _only_fields(item, {"materialIndex", "estimatedMassG"})
        estimates.append(
            MaterialEstimate(
                material_index=_material_index(item.get("materialIndex"), field_name=f"estimates[{index}].materialIndex"),
                estimated_mass_g=_mass(
                    item.get("estimatedMassG"),
                    field_name=f"estimates[{index}].estimatedMassG",
                    allow_zero=False,
                ),
            )
        )
    return tuple(estimates)


def _material_index(value: object, *, field_name: str = "materialIndex") -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _mass(value: object, *, field_name: str, allow_zero: bool) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an exact decimal string")
    try:
        mass = Decimal(value.strip())
    except InvalidOperation as error:
        raise ValueError(f"{field_name} must be an exact decimal string") from error
    if not mass.is_finite() or mass < 0 or (not allow_zero and mass == 0):
        comparator = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{field_name} must be a {comparator} finite decimal")
    return mass


def _optional_text(value: object, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    cleaned = value.strip()
    if len(cleaned) > 512:
        raise ValueError(f"{field_name} must not exceed 512 characters")
    return cleaned or None


def _route_queue_id(request: web.Request) -> UUID:
    raw = request.match_info.get("queue_id", "")
    try:
        return UUID(raw)
    except ValueError as error:
        raise ValueError("queueId must be a UUID") from error


async def _json_object(request: web.Request) -> dict[str, object]:
    if request.content_type != "application/json":
        raise ValueError("request requires application/json")
    try:
        payload = await request.json()
    except Exception as error:
        raise ValueError("request body must be valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


def _only_fields(payload: dict[str, object], allowed: set[str]) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(unknown)}")


def _reserve(
    request: web.Request,
    operation: str,
    payload: object,
    *,
    route_identity: str,
):
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key:
        raise ValueError("Idempotency-Key header is required")
    principal = command_principal(request)
    fingerprint = command_request_fingerprint({"routeIdentity": route_identity, "payload": payload})
    now = datetime.now(UTC)
    return command_idempotency_store(request).reserve(
        CommandIdempotencyRecord(
            principal_id=principal.principal_id,
            operation=operation,
            idempotency_key=key,
            request_fingerprint=fingerprint,
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
    route_identity: str,
    result_ref: str,
    outcome_code: str,
) -> None:
    key = request.headers.get("Idempotency-Key", "").strip()
    principal = command_principal(request)
    command_idempotency_store(request).complete(
        principal_id=principal.principal_id,
        operation=operation,
        idempotency_key=key,
        request_fingerprint=command_request_fingerprint(
            {"routeIdentity": route_identity, "payload": payload}
        ),
        outcome_code=outcome_code,
        result_ref=result_ref,
    )
