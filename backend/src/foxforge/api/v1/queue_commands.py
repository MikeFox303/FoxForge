# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote
from uuid import UUID

from aiohttp import web

from foxforge.application.artifacts import (
    ArtifactFormatConflictError,
    ArtifactHashMismatchError,
    ArtifactNotFoundError,
    ArtifactStorageFullError,
    ArtifactStore,
    ArtifactTooLargeError,
)
from foxforge.application.commands import (
    CommandIdempotencyConflictError,
    CommandIdempotencyRecord,
    CommandIdempotencyState,
    command_request_fingerprint,
)
from foxforge.application.fleet import FleetService
from foxforge.application.queue import (
    QueueEntry,
    QueueEntryNotFoundError,
    QueueEntryState,
    QueueService,
    QueueStoreConflictError,
)
from foxforge.domain.printers.capabilities import (
    MaterialBinding,
    PrintArtifactFormat,
    PrintArtifactSelection,
    PrintExecutionRequest,
)

from .http import add_command_route, command_error, command_idempotency_store, command_principal
from .read_models import _queue_entry
from .security import CommandPermission

DEFAULT_MAX_ARTIFACT_BYTES = 512 * 1024 * 1024


def register_queue_command_routes(
    app: web.Application,
    *,
    queue: QueueService,
    fleet: FleetService,
    artifacts: ArtifactStore,
    max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
) -> None:
    """Register safe artifact staging plus restart-safe queue commands."""

    if max_artifact_bytes <= 0:
        raise ValueError("max_artifact_bytes must be positive")

    async def stage_artifact(request: web.Request) -> web.Response:
        if request.content_type != "application/octet-stream":
            return command_error(
                request,
                status=415,
                code="unsupported_media_type",
                message="Artifact upload requires application/octet-stream.",
            )
        if request.content_length is not None and request.content_length > max_artifact_bytes:
            return command_error(
                request,
                status=413,
                code="artifact_too_large",
                message=f"Artifact exceeds the {max_artifact_bytes}-byte upload limit.",
            )

        try:
            filename = _upload_filename(request.headers.get("X-FoxForge-Filename"))
            artifact_format = _artifact_format(filename)
            expected_sha256 = _sha256_header(request.headers.get("X-FoxForge-Sha256"))
            result = await artifacts.stage(
                filename=filename,
                format=artifact_format,
                expected_sha256=expected_sha256,
                chunks=request.content.iter_chunked(64 * 1024),
                max_size_bytes=max_artifact_bytes,
            )
        except ArtifactTooLargeError as error:
            return command_error(request, status=413, code="artifact_too_large", message=str(error))
        except ArtifactStorageFullError as error:
            return command_error(request, status=507, code="artifact_storage_full", message=str(error))
        except ArtifactHashMismatchError as error:
            return command_error(request, status=400, code="artifact_hash_mismatch", message=str(error))
        except ArtifactFormatConflictError as error:
            return command_error(request, status=409, code="artifact_format_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        payload = _artifact_result(result.artifact, replayed=result.replayed)
        return web.json_response(payload, status=200 if result.replayed else 201)

    async def enqueue(request: web.Request) -> web.Response:
        if request.content_type != "application/json":
            return command_error(
                request,
                status=415,
                code="unsupported_media_type",
                message="Queue commands require application/json.",
            )
        try:
            payload = await _json_object(request)
            _only_fields(
                payload,
                {
                    "queueId",
                    "dispatchId",
                    "printerId",
                    "artifactId",
                    "selection",
                    "materialBindings",
                    "requestedName",
                },
            )
            queue_id = _uuid(payload.get("queueId"), "queueId")
            dispatch_id = _uuid(payload.get("dispatchId"), "dispatchId")
            printer_id = _required_text(payload, "printerId")
            if printer_id not in fleet.printer_ids:
                return command_error(request, status=404, code="printer_not_found", message="Printer was not found.")
            artifact_id = _sha256_value(payload.get("artifactId"), "artifactId")
            artifact = artifacts.get(artifact_id)
            selection = _selection(payload.get("selection"))
            bindings = _material_bindings(payload.get("materialBindings"))
            requested_name = _optional_text(payload.get("requestedName"), field_name="requestedName")
            expected_request = PrintExecutionRequest(
                dispatch_id=dispatch_id,
                artifact=artifact,
                selection=selection,
                material_bindings=bindings,
                requested_name=requested_name,
            )
            reservation = _reserve(request, "queue.enqueue", payload)
        except ArtifactNotFoundError:
            return command_error(request, status=404, code="artifact_not_found", message="Artifact was not found.")
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            replay = _existing_enqueue(queue, queue_id, printer_id, expected_request)
            if replay is None:
                return command_error(
                    request,
                    status=409,
                    code="reconciliation_required",
                    message="The previous enqueue outcome cannot be confirmed safely.",
                )
            _complete(request, "queue.enqueue", payload, result_ref=str(queue_id), outcome_code=replay.state.value)
            return web.json_response(_queue_result(replay, replayed=True))

        try:
            entry = queue.enqueue(
                printer_id,
                artifact,
                selection=selection,
                material_bindings=bindings,
                requested_name=requested_name,
                queue_id=queue_id,
                dispatch_id=dispatch_id,
            )
        except QueueStoreConflictError:
            replay = _existing_enqueue(queue, queue_id, printer_id, expected_request)
            if replay is None:
                return command_error(request, status=409, code="queue_exists", message="queueId is already in use")
            entry = replay

        _complete(request, "queue.enqueue", payload, result_ref=str(queue_id), outcome_code=entry.state.value)
        return web.json_response(_queue_result(entry), status=201)

    async def dispatch(request: web.Request) -> web.Response:
        try:
            queue_id = _route_queue_id(request)
            entry = queue.get(queue_id)
        except (ValueError, TypeError):
            return command_error(request, status=400, code="invalid_request", message="queueId must be a UUID")
        except QueueEntryNotFoundError:
            return command_error(request, status=404, code="queue_not_found", message="Queue entry was not found.")

        unsafe = _dispatch_conflict(entry)
        if unsafe is not None:
            return command_error(request, status=409, code=unsafe[0], message=unsafe[1])
        if entry.printer_id not in fleet.printer_ids:
            return command_error(request, status=404, code="printer_not_found", message="Printer was not found.")

        payload: dict[str, object] = {}
        try:
            reservation = _reserve(request, "queue.dispatch", payload, route_identity=str(queue_id))
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except ValueError as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            if reservation.record.state == CommandIdempotencyState.COMPLETED:
                return web.json_response(_queue_result(queue.get(queue_id), replayed=True))
            return command_error(
                request,
                status=409,
                code="reconciliation_required",
                message="A previous dispatch command with this idempotency key is still unresolved.",
            )

        entry = await queue.dispatch(queue_id)
        _complete(
            request,
            "queue.dispatch",
            payload,
            route_identity=str(queue_id),
            result_ref=str(queue_id),
            outcome_code=entry.state.value,
        )
        result = _queue_result(entry)
        result["reconciliationRequired"] = entry.state == QueueEntryState.INDETERMINATE
        return web.json_response(result)

    async def reconcile(request: web.Request) -> web.Response:
        try:
            queue_id = _route_queue_id(request)
            current = queue.get(queue_id)
        except (ValueError, TypeError):
            return command_error(request, status=400, code="invalid_request", message="queueId must be a UUID")
        except QueueEntryNotFoundError:
            return command_error(request, status=404, code="queue_not_found", message="Queue entry was not found.")

        if current.state not in {QueueEntryState.DISPATCHING, QueueEntryState.INDETERMINATE}:
            return command_error(
                request,
                status=409,
                code="invalid_queue_state",
                message="Only dispatching or indeterminate queue entries can be reconciled.",
            )
        if request.content_type != "application/json":
            return command_error(
                request,
                status=415,
                code="unsupported_media_type",
                message="Queue commands require application/json.",
            )

        try:
            payload = await _json_object(request)
            _only_fields(payload, {"accepted", "vendorJobId", "acceptedAt"})
            accepted = payload.get("accepted")
            if not isinstance(accepted, bool):
                raise ValueError("accepted must be a boolean")
            vendor_job_id = _optional_text(payload.get("vendorJobId"), field_name="vendorJobId")
            accepted_at = _optional_datetime(payload.get("acceptedAt"), field_name="acceptedAt")
            if not accepted and (vendor_job_id is not None or accepted_at is not None):
                raise ValueError("vendorJobId and acceptedAt are valid only when accepted is true")
            reservation = _reserve(request, "queue.reconcile", payload, route_identity=str(queue_id))
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            if reservation.record.state == CommandIdempotencyState.COMPLETED:
                return web.json_response(_queue_result(queue.get(queue_id), replayed=True))
            return command_error(
                request,
                status=409,
                code="reconciliation_required",
                message="A previous reconciliation command with this idempotency key is still unresolved.",
            )

        try:
            entry = queue.resolve_reconciliation(
                queue_id,
                accepted=accepted,
                vendor_job_id=vendor_job_id,
                accepted_at=accepted_at,
            )
        except ValueError as error:
            return command_error(request, status=409, code="invalid_queue_state", message=str(error))

        _complete(
            request,
            "queue.reconcile",
            payload,
            route_identity=str(queue_id),
            result_ref=str(queue_id),
            outcome_code=entry.state.value,
        )
        return web.json_response(_queue_result(entry))

    add_command_route(app, "POST", "/api/v1/artifacts", CommandPermission.QUEUE_WRITE, stage_artifact)
    add_command_route(app, "POST", "/api/v1/queue", CommandPermission.QUEUE_WRITE, enqueue)
    add_command_route(
        app,
        "POST",
        "/api/v1/queue/{queue_id}/dispatch",
        CommandPermission.QUEUE_WRITE,
        dispatch,
    )
    add_command_route(
        app,
        "POST",
        "/api/v1/queue/{queue_id}/reconcile",
        CommandPermission.QUEUE_WRITE,
        reconcile,
    )


def _dispatch_conflict(entry: QueueEntry) -> tuple[str, str] | None:
    if entry.state in {QueueEntryState.DISPATCHING, QueueEntryState.INDETERMINATE}:
        return (
            "queue_reconciliation_required",
            "This queue entry has an uncertain dispatch outcome and must be reconciled before any retry.",
        )
    if entry.state == QueueEntryState.FAILED:
        if entry.receipt is not None:
            return "queue_already_started", "A receipt-bearing failed print must never be redispatched."
        if entry.error is None or not entry.error.retryable:
            return "queue_not_retryable", "The previous dispatch failure is not marked retryable."
    return None


def _existing_enqueue(
    queue: QueueService,
    queue_id: UUID,
    printer_id: str,
    expected_request: PrintExecutionRequest,
) -> QueueEntry | None:
    try:
        existing = queue.get(queue_id)
    except QueueEntryNotFoundError:
        return None
    if existing.printer_id != printer_id or not _same_client_enqueue_intent(existing.request, expected_request):
        return None
    return existing


def _same_client_enqueue_intent(existing: PrintExecutionRequest, expected: PrintExecutionRequest) -> bool:
    existing_bindings = tuple(sorted((item.material_index, item.slot_id) for item in existing.material_bindings))
    expected_bindings = tuple(sorted((item.material_index, item.slot_id) for item in expected.material_bindings))
    return (
        existing.dispatch_id == expected.dispatch_id
        and existing.artifact == expected.artifact
        and existing.selection == expected.selection
        and existing.requested_name == expected.requested_name
        and existing_bindings == expected_bindings
    )


def _queue_result(entry: QueueEntry, *, replayed: bool = False) -> dict[str, Any]:
    result = _queue_entry(entry)
    result["replayed"] = replayed
    return result


def _artifact_result(artifact, *, replayed: bool) -> dict[str, object]:
    return {
        "artifactId": artifact.artifact_id,
        "filename": artifact.filename,
        "format": artifact.format.value,
        "sizeBytes": artifact.size_bytes,
        "sha256": artifact.sha256,
        "replayed": replayed,
    }


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
    outcome_code: str,
    route_identity: str | None = None,
) -> None:
    principal = command_principal(request)
    fingerprint_payload = {"routeIdentity": route_identity, "payload": payload}
    command_idempotency_store(request).complete(
        principal_id=principal.principal_id,
        operation=operation,
        idempotency_key=_idempotency_key(request),
        request_fingerprint=command_request_fingerprint(fingerprint_payload),
        outcome_code=outcome_code,
        result_ref=result_ref,
    )


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


def _route_queue_id(request: web.Request) -> UUID:
    return _uuid(request.match_info.get("queue_id"), "queueId")


def _required_text(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    cleaned = value.strip()
    if len(cleaned) > 256:
        raise ValueError(f"{field_name} must not exceed 256 characters")
    return cleaned


def _optional_text(value: object, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    cleaned = value.strip()
    if len(cleaned) > 256:
        raise ValueError(f"{field_name} must not exceed 256 characters")
    return cleaned or None


def _sha256_value(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a SHA-256 string")
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{field_name} must contain 64 hexadecimal characters")
    return normalized


def _sha256_header(value: str | None) -> str:
    return _sha256_value(value, "X-FoxForge-Sha256")


def _upload_filename(value: str | None) -> str:
    if value is None or not value:
        raise ValueError("X-FoxForge-Filename header is required")
    try:
        filename = unquote(value, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("X-FoxForge-Filename must be percent-encoded UTF-8") from error
    if not filename or filename in {".", ".."} or "/" in filename or "\\" in filename:
        raise ValueError("X-FoxForge-Filename must contain a base filename, not a path")
    if len(filename) > 180 or any(ord(character) < 0x20 or ord(character) == 0x7F for character in filename):
        raise ValueError("X-FoxForge-Filename is invalid or too long")
    return filename


def _artifact_format(filename: str) -> PrintArtifactFormat:
    lowered = filename.lower()
    if lowered.endswith(".gcode"):
        return PrintArtifactFormat.GCODE
    if lowered.endswith(".3mf"):
        return PrintArtifactFormat.THREE_MF
    raise ValueError("artifact filename must end in .gcode or .3mf")


def _selection(value: object) -> PrintArtifactSelection | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("selection must be an object or null")
    _only_fields(value, {"plateIndex"})
    plate_index = value.get("plateIndex")
    if plate_index is not None and (not isinstance(plate_index, int) or isinstance(plate_index, bool)):
        raise ValueError("selection.plateIndex must be an integer or null")
    return PrintArtifactSelection(plate_index=plate_index)


def _material_bindings(value: object) -> tuple[MaterialBinding, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("materialBindings must be an array")
    bindings: list[MaterialBinding] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"materialBindings[{index}] must be an object")
        _only_fields(item, {"materialIndex", "slotId"})
        material_index = item.get("materialIndex")
        if not isinstance(material_index, int) or isinstance(material_index, bool):
            raise ValueError(f"materialBindings[{index}].materialIndex must be an integer")
        slot_id = item.get("slotId")
        if not isinstance(slot_id, str) or not slot_id.strip():
            raise ValueError(f"materialBindings[{index}].slotId must be a non-empty string")
        bindings.append(MaterialBinding(material_index=material_index, slot_id=slot_id.strip()))
    return tuple(bindings)


def _optional_datetime(value: object, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an ISO 8601 timestamp or null")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO 8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed.astimezone(UTC)
