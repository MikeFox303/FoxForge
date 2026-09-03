# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from uuid import UUID

from foxforge.application.queue import (
    QueueDispatchError,
    QueueEntry,
    QueueEntryState,
    QueueStoreConflictError,
    QueueStoreMissingError,
)
from foxforge.domain.printers import PrinterErrorCode
from foxforge.domain.printers.capabilities import (
    LocalPrintArtifact,
    MaterialBinding,
    PrintArtifactFormat,
    PrintArtifactSelection,
    PrintAssessmentBlocker,
    PrintAssessmentBlockerCode,
    PrintDispatchReceipt,
    PrintExecutionAssessment,
    PrintExecutionRequest,
)

_SCHEMA_VERSION = 1


class SQLiteQueueStore:
    """Small durable queue store suited to FoxForge's single-container v1.

    Each queue entry is stored as a versioned JSON payload in SQLite. Keeping
    the application model serialization explicit makes process-restart
    idempotency testable now while leaving room for a later normalized schema.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def path(self) -> Path:
        return self._path

    def create(self, entry: QueueEntry) -> None:
        payload = _encode_entry(entry)
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    "INSERT INTO queue_entries(queue_id, payload, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (
                        str(entry.queue_id),
                        payload,
                        entry.created_at.isoformat(),
                        entry.updated_at.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise QueueStoreConflictError(entry.queue_id) from error

    def save(self, entry: QueueEntry) -> None:
        payload = _encode_entry(entry)
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "UPDATE queue_entries SET payload = ?, updated_at = ? WHERE queue_id = ?",
                (payload, entry.updated_at.isoformat(), str(entry.queue_id)),
            )
            if cursor.rowcount != 1:
                raise QueueStoreMissingError(entry.queue_id)

    def get(self, queue_id: UUID) -> QueueEntry | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM queue_entries WHERE queue_id = ?",
                (str(queue_id),),
            ).fetchone()
        return None if row is None else _decode_entry(row[0])

    def list(self) -> tuple[QueueEntry, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT payload FROM queue_entries ORDER BY created_at ASC, queue_id ASC"
            ).fetchall()
        return tuple(_decode_entry(row[0]) for row in rows)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS queue_entries (
                    queue_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA foreign_keys=ON")
        return connection


def _encode_entry(entry: QueueEntry) -> str:
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "queue_id": str(entry.queue_id),
        "printer_id": entry.printer_id,
        "request": _encode_request(entry.request),
        "state": entry.state.value,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
        "assessment": _encode_assessment(entry.assessment),
        "receipt": _encode_receipt(entry.receipt),
        "error": _encode_error(entry.error),
        "attempt_count": entry.attempt_count,
        "last_attempt_at": entry.last_attempt_at.isoformat() if entry.last_attempt_at else None,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _decode_entry(raw: str) -> QueueEntry:
    payload = json.loads(raw)
    if payload.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError(f"unsupported queue entry schema version: {payload.get('schema_version')!r}")

    return QueueEntry(
        queue_id=UUID(payload["queue_id"]),
        printer_id=payload["printer_id"],
        request=_decode_request(payload["request"]),
        state=QueueEntryState(payload["state"]),
        created_at=_parse_datetime(payload["created_at"]),
        updated_at=_parse_datetime(payload["updated_at"]),
        assessment=_decode_assessment(payload["assessment"]),
        receipt=_decode_receipt(payload["receipt"]),
        error=_decode_error(payload["error"]),
        attempt_count=int(payload["attempt_count"]),
        last_attempt_at=(
            _parse_datetime(payload["last_attempt_at"])
            if payload.get("last_attempt_at") is not None
            else None
        ),
    )


def _encode_request(request: PrintExecutionRequest) -> dict[str, object]:
    artifact = request.artifact
    return {
        "dispatch_id": str(request.dispatch_id),
        "artifact": {
            "artifact_id": artifact.artifact_id,
            "path": str(artifact.path),
            "filename": artifact.filename,
            "format": artifact.format.value,
            "size_bytes": artifact.size_bytes,
            "sha256": artifact.sha256,
        },
        "selection": (
            {"plate_index": request.selection.plate_index}
            if request.selection is not None
            else None
        ),
        "material_bindings": [
            {"material_index": binding.material_index, "slot_id": binding.slot_id}
            for binding in request.material_bindings
        ],
        "requested_name": request.requested_name,
    }


def _decode_request(payload: dict[str, object]) -> PrintExecutionRequest:
    artifact_payload = _require_dict(payload["artifact"])
    selection_payload = payload.get("selection")
    raw_bindings = payload.get("material_bindings", [])
    if not isinstance(raw_bindings, list):
        raise ValueError("material_bindings must be a list")

    artifact = LocalPrintArtifact(
        artifact_id=str(artifact_payload["artifact_id"]),
        path=Path(str(artifact_payload["path"])),
        filename=str(artifact_payload["filename"]),
        format=PrintArtifactFormat(str(artifact_payload["format"])),
        size_bytes=int(artifact_payload["size_bytes"]),
        sha256=str(artifact_payload["sha256"]),
    )
    selection = None
    if selection_payload is not None:
        selection_dict = _require_dict(selection_payload)
        plate_index = selection_dict.get("plate_index")
        selection = PrintArtifactSelection(plate_index=None if plate_index is None else int(plate_index))

    bindings = tuple(
        MaterialBinding(
            material_index=int(_require_dict(binding)["material_index"]),
            slot_id=str(_require_dict(binding)["slot_id"]),
        )
        for binding in raw_bindings
    )
    return PrintExecutionRequest(
        dispatch_id=UUID(str(payload["dispatch_id"])),
        artifact=artifact,
        selection=selection,
        material_bindings=bindings,
        requested_name=(None if payload.get("requested_name") is None else str(payload["requested_name"])),
    )


def _encode_assessment(assessment: PrintExecutionAssessment | None) -> dict[str, object] | None:
    if assessment is None:
        return None
    return {
        "eligible": assessment.eligible,
        "blockers": [
            {"code": blocker.code.value, "message": blocker.message}
            for blocker in assessment.blockers
        ],
        "observed_at": assessment.observed_at.isoformat(),
    }


def _decode_assessment(payload: object) -> PrintExecutionAssessment | None:
    if payload is None:
        return None
    data = _require_dict(payload)
    raw_blockers = data.get("blockers", [])
    if not isinstance(raw_blockers, list):
        raise ValueError("assessment blockers must be a list")
    blockers: list[PrintAssessmentBlocker] = []
    for blocker in raw_blockers:
        blocker_data = _require_dict(blocker)
        blockers.append(
            PrintAssessmentBlocker(
                code=PrintAssessmentBlockerCode(str(blocker_data["code"])),
                message=(None if blocker_data.get("message") is None else str(blocker_data["message"])),
            )
        )
    return PrintExecutionAssessment(
        eligible=bool(data["eligible"]),
        blockers=tuple(blockers),
        observed_at=_parse_datetime(str(data["observed_at"])),
    )


def _encode_receipt(receipt: PrintDispatchReceipt | None) -> dict[str, object] | None:
    if receipt is None:
        return None
    return {
        "dispatch_id": str(receipt.dispatch_id),
        "accepted_at": receipt.accepted_at.isoformat(),
        "vendor_job_id": receipt.vendor_job_id,
        "artifact_sha256": receipt.artifact_sha256,
    }


def _decode_receipt(payload: object) -> PrintDispatchReceipt | None:
    if payload is None:
        return None
    data = _require_dict(payload)
    return PrintDispatchReceipt(
        dispatch_id=UUID(str(data["dispatch_id"])),
        accepted_at=_parse_datetime(str(data["accepted_at"])),
        vendor_job_id=None if data.get("vendor_job_id") is None else str(data["vendor_job_id"]),
        artifact_sha256=str(data["artifact_sha256"]),
    )


def _encode_error(error: QueueDispatchError | None) -> dict[str, object] | None:
    if error is None:
        return None
    return {
        "code": error.code.value,
        "message": error.message,
        "retryable": error.retryable,
        "vendor_code": error.vendor_code,
    }


def _decode_error(payload: object) -> QueueDispatchError | None:
    if payload is None:
        return None
    data = _require_dict(payload)
    return QueueDispatchError(
        code=PrinterErrorCode(str(data["code"])),
        message=str(data["message"]),
        retryable=bool(data["retryable"]),
        vendor_code=None if data.get("vendor_code") is None else str(data["vendor_code"]),
    )


def _require_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("queue payload object must be a mapping")
    return value


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
