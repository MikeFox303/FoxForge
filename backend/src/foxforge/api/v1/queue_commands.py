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
            reservation = _reserve(request, "queue.dispatch", {"queueId": str(queue_id)})
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            existing = queue.get(queue_id)
            if existing is None:
                return command_error(
                    request,
                    status=409,
                    code="reconciliation_required",
                    message="Dispatch outcome is unknown.",
                )
            if reservation.record.state == CommandIdempotencyState.STARTED:
                return command_error(
                    request,
                    status=409,
                    code="reconciliation_required",
                    message="The previous dispatch outcome requires reconciliation.",
                )
            return web.json_response(_queue_result(existing, replayed=True))

        try:
            entry = await queue.dispatch(queue_id)
        except QueueEntryNotFoundError:
            return command_error(request, status=404, code="queue_not_found", message="Queue entry was not found.")

        if entry.state == QueueEntryState.INDETERMINATE:
            return web.json_response(_queue_result(entry), status=409)

        _complete(
            request,
            "queue.dispatch",
            {"queueId": str(queue_id)},
            result_ref=str(queue_id),
            outcome_code=entry.state.value,
        )
        return web.json_response(_queue_result(entry))

    async def reconcile(request: web.Request) -> web.Response:
        try:
            queue_id = _route_queue_id(request)
            payload = await _json_object(request)
            _only_fields(payload, {"state"})
            state = QueueEntryState(_required_text(payload, "state"))
            reservation_payload = {"queueId": str(queue_id), "state": state.value}
            reservation = _reserve(request, "queue.reconcile", reservation_payload)
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            existing = queue.get(queue_id)
            if existing is None:
                return command_error(
                    request,
                    status=409,
                    code="reconciliation_required",
                    message="Reconcile outcome is unknown.",
                )
            return web.json_response(_queue_result(existing, replayed=True))

        try:
            entry = queue.reconcile(queue_id, state)
        except QueueEntryNotFoundError:
            return command_error(request, status=404, code="queue_not_found", message="Queue entry was not found.")

        _complete(
            request,
            "queue.reconcile",
            reservation_payload,
            result_ref=str(queue_id),
            outcome_code=entry.state.value,
        )
        return web.json_response(_queue_result(entry))

    add_command_route(
        app,
        "POST",
        "/api/v1/artifacts",
        stage_artifact,
        permission=CommandPermission.QUEUE_MUTATE,
        operation="artifact.stage",
    )
    add_command_route(
        app,
        "POST",
        "/api/v1/queue",
        enqueue,
        permission=CommandPermission.QUEUE_MUTATE,
        operation="queue.enqueue",
    )
    add_command_route(
        app,
        "POST",
        "/api/v1/queue/{queue_id}/dispatch",
        dispatch,
        permission=CommandPermission.QUEUE_MUTATE,
        operation="queue.dispatch",
    )
    add_command_route(
        app,
        "POST",
        "/api/v1/queue/{queue_id}/reconcile",
        reconcile,
        permission=CommandPermission.QUEUE_MUTATE,
        operation="queue.reconcile",
    )


def _reserve(request: web.Request, operation: str, payload: dict[str, Any]):
    store = command_idempotency_store(request)
    principal = command_principal(request)
    key = _idempotency_key(request)
    fingerprint = command_request_fingerprint(payload)
    record = CommandIdempotencyRecord.started(
        principal_id=principal.principal_id,
        operation=operation,
        idempotency_key=key,
        request_fingerprint=fingerprint,
        now=datetime.now(UTC),
    )
    return store.reserve(record)


def _complete(
    request: web.Request,
    operation: str,
    payload: dict[str, Any],
    *,
    result_ref: str,
    outcome_code: str,
) -> None:
    principal = command_principal(request)
    command_idempotency_store(request).complete(
        principal_id=principal.principal_id,
        operation=operation,
        idempotency_key=_idempotency_key(request),
        request_fingerprint=command_request_fingerprint(payload),
        result_ref=result_ref,
        outcome_code=outcome_code,
        completed_at=datetime.now(UTC),
    )


def _idempotency_key(request: web.Request) -> str:
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key:
        raise ValueError("Idempotency-Key is required")
    if len(key) > 200:
        raise ValueError("Idempotency-Key is too long")
    return key


def _upload_filename(raw: str | None) -> str:
    if raw is None:
        raise ValueError("X-FoxForge-Filename is required")
    filename = unquote(raw).strip()
    if not filename or len(filename) > 255:
        raise ValueError("X-FoxForge-Filename is invalid")
    if "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise ValueError("X-FoxForge-Filename must be a basename")
    return filename


def _artifact_format(filename: str) -> PrintArtifactFormat:
    lowered = filename.lower()
    if lowered.endswith(".gcode.3mf") or lowered.endswith(".3mf"):
        return PrintArtifactFormat.THREE_MF
    if lowered.endswith(".gcode"):
        return PrintArtifactFormat.GCODE
    raise ValueError("supported artifact extensions are .gcode and .3mf")


def _sha256_header(raw: str | None) -> str:
    if raw is None:
        raise ValueError("X-FoxForge-Sha256 is required")
    return _sha256_value(raw, "X-FoxForge-Sha256")


def _sha256_value(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a SHA-256 string")
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{field_name} must contain 64 hexadecimal characters")
    return normalized


def _json_object(request: web.Request):
    async def load() -> dict[str, Any]:
        try:
            value = await request.json()
        except Exception as error:
            raise ValueError("request body must be valid JSON") from error
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    return load()


def _only_fields(payload: dict[str, Any], allowed: set[str]) -> None:
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError("unknown request fields: " + ", ".join(sorted(unknown)))


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _optional_text(value: object, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    cleaned = value.strip()
    return cleaned or None


def _uuid(value: object, field_name: str) -> UUID:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a UUID string") from error


def _route_queue_id(request: web.Request) -> UUID:
    try:
        return UUID(request.match_info["queue_id"])
    except (KeyError, ValueError) as error:
        raise ValueError("queue_id must be a UUID") from error


def _selection(value: object) -> PrintArtifactSelection:
    if value is None:
        return PrintArtifactSelection()
    if not isinstance(value, dict):
        raise ValueError("selection must be an object")
    _only_fields(value, {"plate", "objectIds"})
    plate = value.get("plate")
    if plate is not None and (not isinstance(plate, int) or isinstance(plate, bool) or plate < 0):
        raise ValueError("selection.plate must be a non-negative integer or null")
    object_ids = value.get("objectIds", [])
    if not isinstance(object_ids, list) or not all(isinstance(item, str) and item.strip() for item in object_ids):
        raise ValueError("selection.objectIds must contain non-empty strings")
    return PrintArtifactSelection(plate=plate, object_ids=tuple(item.strip() for item in object_ids))


def _material_bindings(value: object) -> tuple[MaterialBinding, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("materialBindings must be an array")
    bindings: list[MaterialBinding] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("materialBindings entries must be objects")
        _only_fields(item, {"sourceId", "slotId"})
        bindings.append(
            MaterialBinding(
                source_id=_required_text(item, "sourceId"),
                slot_id=_required_text(item, "slotId"),
            )
        )
    return tuple(bindings)


def _artifact_result(artifact, *, replayed: bool) -> dict[str, Any]:
    return {
        "apiVersion": "1",
        "artifactId": artifact.artifact_id,
        "filename": artifact.filename,
        "format": artifact.format.value,
        "sizeBytes": artifact.size_bytes,
        "sha256": artifact.sha256,
        "replayed": replayed,
    }


def _queue_result(entry: QueueEntry, *, replayed: bool = False) -> dict[str, Any]:
    payload = {"apiVersion": "1", "entry": _queue_entry(entry)}
    if replayed:
        payload["replayed"] = True
    return payload


def _existing_enqueue(
    queue: QueueService,
    queue_id: UUID,
    printer_id: str,
    expected_request: PrintExecutionRequest,
) -> QueueEntry | None:
    existing = queue.get(queue_id)
    if existing is None:
        return None
    if existing.printer_id != printer_id or existing.request != expected_request:
        return None
    return existing
