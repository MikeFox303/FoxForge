# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from aiohttp import web

from foxforge.application.commands import (
    CommandIdempotencyConflictError,
    CommandIdempotencyRecord,
    CommandIdempotencyState,
    command_request_fingerprint,
)
from foxforge.application.fleet import FleetService
from foxforge.domain.printers import PrinterAdapterError, PrinterErrorCode
from foxforge.domain.printers.capabilities import JobControlAction, JobControlCapability, JobControlRequest

from .http import add_command_route, command_error, command_idempotency_store, command_principal
from .security import CommandPermission


def register_job_control_command_routes(app: web.Application, *, fleet: FleetService) -> None:
    """Register ADR 0004 guarded pause/resume/cancel commands."""

    async def control_job(request: web.Request) -> web.Response:
        printer_id = request.match_info.get("printer_id", "")
        if printer_id not in fleet.printer_ids:
            return command_error(request, status=404, code="printer_not_found", message="Printer was not found.")
        if request.content_type != "application/json":
            return command_error(
                request,
                status=415,
                code="unsupported_media_type",
                message="Job-control commands require application/json.",
            )

        try:
            payload = await _json_object(request)
            _only_fields(payload, {"controlId", "action", "expectedVendorJobId"})
            control_id = _uuid(payload.get("controlId"), "controlId")
            action = _action(payload.get("action"))
            vendor_job_id = _required_text(payload.get("expectedVendorJobId"), "expectedVendorJobId")
            reservation = _reserve(request, payload, printer_id=printer_id)
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            if reservation.record.state == CommandIdempotencyState.COMPLETED:
                return _completed_replay(
                    request,
                    reservation.record.outcome_code,
                    printer_id=printer_id,
                    control_id=control_id,
                    action=action,
                    vendor_job_id=vendor_job_id,
                )
            return command_error(
                request,
                status=409,
                code="job_control_reconciliation_required",
                message=(
                    "A previous job-control command with this idempotency key has an unresolved outcome. "
                    "Do not resend the side effect; reconcile against the live printer state first."
                ),
                retryable=False,
            )

        capability = fleet.capability(printer_id, JobControlCapability)
        if capability is None:
            _complete(request, payload, printer_id=printer_id, control_id=control_id, outcome_code="error:unsupported")
            return command_error(
                request,
                status=409,
                code="job_control_unsupported",
                message="This printer does not expose the common job-control capability.",
            )

        job_request = JobControlRequest(
            control_id=control_id,
            action=action,
            expected_vendor_job_id=vendor_job_id,
        )
        try:
            receipt = await capability.execute(job_request)
        except PrinterAdapterError as error:
            if error.code == PrinterErrorCode.INDETERMINATE:
                return command_error(
                    request,
                    status=409,
                    code="job_control_indeterminate",
                    message=(
                        "FoxForge cannot prove whether the printer applied this control command. "
                        "Do not blindly retry it; inspect the live job state first."
                    ),
                    retryable=False,
                )
            _complete(
                request,
                payload,
                printer_id=printer_id,
                control_id=control_id,
                outcome_code=f"error:{error.code.value}",
            )
            status, code = _api_error(error.code)
            return command_error(
                request,
                status=status,
                code=code,
                message=error.message,
                retryable=error.retryable,
            )

        _complete(
            request,
            payload,
            printer_id=printer_id,
            control_id=control_id,
            outcome_code="accepted",
        )
        return web.json_response(
            {
                "controlId": str(receipt.control_id),
                "printerId": printer_id,
                "action": receipt.action.value,
                "vendorJobId": receipt.vendor_job_id,
                "accepted": True,
                "replayed": False,
            }
        )

    add_command_route(
        app,
        "POST",
        "/api/v1/printers/{printer_id}/job-control",
        CommandPermission.PRINTER_CONTROL,
        control_job,
    )


def _reserve(request: web.Request, payload: object, *, printer_id: str):
    key = _idempotency_key(request)
    principal = command_principal(request)
    now = datetime.now(UTC)
    fingerprint_payload = {"routeIdentity": printer_id, "payload": payload}
    return command_idempotency_store(request).reserve(
        CommandIdempotencyRecord(
            principal_id=principal.principal_id,
            operation="printer.job_control",
            idempotency_key=key,
            request_fingerprint=command_request_fingerprint(fingerprint_payload),
            state=CommandIdempotencyState.STARTED,
            created_at=now,
            updated_at=now,
        )
    )


def _complete(
    request: web.Request,
    payload: object,
    *,
    printer_id: str,
    control_id: UUID,
    outcome_code: str,
) -> None:
    principal = command_principal(request)
    command_idempotency_store(request).complete(
        principal_id=principal.principal_id,
        operation="printer.job_control",
        idempotency_key=_idempotency_key(request),
        request_fingerprint=command_request_fingerprint({"routeIdentity": printer_id, "payload": payload}),
        outcome_code=outcome_code,
        result_ref=str(control_id),
    )


def _completed_replay(
    request: web.Request,
    outcome_code: str | None,
    *,
    printer_id: str,
    control_id: UUID,
    action: JobControlAction,
    vendor_job_id: str,
) -> web.Response:
    if outcome_code == "accepted":
        return web.json_response(
            {
                "controlId": str(control_id),
                "printerId": printer_id,
                "action": action.value,
                "vendorJobId": vendor_job_id,
                "accepted": True,
                "replayed": True,
            }
        )
    if outcome_code and outcome_code.startswith("error:"):
        raw = outcome_code.removeprefix("error:")
        try:
            adapter_code = PrinterErrorCode(raw)
        except ValueError:
            adapter_code = PrinterErrorCode.INTERNAL_ADAPTER_ERROR
        status, code = _api_error(adapter_code)
        return command_error(
            request,
            status=status,
            code=code,
            message=f"The previous job-control command completed with {adapter_code.value}.",
            retryable=adapter_code
            in {
                PrinterErrorCode.CONNECTION_UNAVAILABLE,
                PrinterErrorCode.TIMEOUT,
                PrinterErrorCode.BUSY,
                PrinterErrorCode.NOT_READY,
            },
        )
    return command_error(
        request,
        status=409,
        code="job_control_reconciliation_required",
        message="The previous job-control outcome cannot be reconstructed safely.",
    )


def _api_error(code: PrinterErrorCode) -> tuple[int, str]:
    if code == PrinterErrorCode.INVALID_REQUEST:
        return 400, "invalid_request"
    if code == PrinterErrorCode.UNSUPPORTED:
        return 409, "job_control_unsupported"
    if code == PrinterErrorCode.CONFLICT:
        return 409, "job_control_conflict"
    if code == PrinterErrorCode.BUSY:
        return 409, "printer_busy"
    if code == PrinterErrorCode.NOT_READY:
        return 409, "printer_not_ready"
    if code == PrinterErrorCode.CONNECTION_UNAVAILABLE:
        return 409, "printer_unavailable"
    if code == PrinterErrorCode.AUTHENTICATION_FAILED:
        return 502, "printer_authentication_failed"
    if code == PrinterErrorCode.REMOTE_REJECTED:
        return 409, "remote_rejected"
    if code == PrinterErrorCode.TIMEOUT:
        return 504, "printer_timeout"
    if code == PrinterErrorCode.INDETERMINATE:
        return 409, "job_control_indeterminate"
    return 502, "printer_control_failed"


def _idempotency_key(request: web.Request) -> str:
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key:
        raise ValueError("Idempotency-Key header is required")
    return key


async def _json_object(request: web.Request) -> dict[str, object]:
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


def _uuid(value: object, field_name: str) -> UUID:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a UUID string") from error


def _action(value: object) -> JobControlAction:
    if not isinstance(value, str):
        raise ValueError("action must be pause, resume or cancel")
    try:
        return JobControlAction(value.strip().lower())
    except ValueError as error:
        raise ValueError("action must be pause, resume or cancel") from error


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    cleaned = value.strip()
    if len(cleaned) > 256:
        raise ValueError(f"{field_name} must not exceed 256 characters")
    return cleaned
