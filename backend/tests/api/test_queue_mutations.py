# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import hashlib
from uuid import UUID

from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1 import BearerCommandSecurity, create_api_v1_app
from foxforge.api.v1.command_audit import install_command_audit
from foxforge.api.v1.queue_commands import register_queue_command_routes
from foxforge.api.v1.queue_guard import install_queue_command_guard
from foxforge.application.commands import (
    CommandAuditOutcome,
    InMemoryCommandAuditStore,
    InMemoryCommandIdempotencyStore,
    command_idempotency_key_digest,
)
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueService
from foxforge.domain.printers import PrinterIdentity
from foxforge.infrastructure.artifacts import FilesystemArtifactStore
from foxforge.testing import build_fake_printer

_TOKEN = "queue-command-token-0123456789abcdef"
_QUEUE_ID = "153b6d90-5bb1-49fd-b90a-4316ba57db88"
_DISPATCH_ID = "b9132e98-22d5-43ae-8d4f-f52c72bc921e"
_QUEUE_ID_2 = "12effdc1-2f96-487d-a389-37a95e7edc37"
_DISPATCH_ID_2 = "19967b0e-aaf4-4511-a507-791229221e4a"


def _command_headers(key: str, request_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_TOKEN}",
        "Idempotency-Key": key,
        "X-Request-Id": request_id,
    }


def _build_app(tmp_path):
    identity = PrinterIdentity(
        printer_id="x2d-main",
        display_name="Bambu X2D",
        vendor="bambu_lab",
        model="X2D",
        serial_number="SERIAL",
        adapter_kind="fake",
    )
    adapter, printing, _ = build_fake_printer(identity)
    fleet = FleetService([adapter])
    queue = QueueService(fleet, InMemoryQueueStore())
    audit = InMemoryCommandAuditStore()
    idempotency = InMemoryCommandIdempotencyStore()
    security = BearerCommandSecurity(_TOKEN)
    app = create_api_v1_app(
        fleet=fleet,
        queue=queue,
        inventory=InventoryService(InMemoryInventoryStore()),
        command_security=security,
        command_idempotency=idempotency,
    )
    artifacts = FilesystemArtifactStore(tmp_path / "artifacts")
    register_queue_command_routes(
        app,
        queue=queue,
        fleet=fleet,
        artifacts=artifacts,
        max_artifact_bytes=1024,
    )
    install_command_audit(app, security=security, store=audit)
    install_queue_command_guard(
        app,
        queue=queue,
        security=security,
        idempotency=idempotency,
    )
    return app, fleet, queue, printing, audit


async def _upload(client: TestClient, payload: bytes) -> str:
    digest = hashlib.sha256(payload).hexdigest()
    response = await client.post(
        "/api/v1/artifacts",
        data=payload,
        headers={
            "Authorization": f"Bearer {_TOKEN}",
            "Content-Type": "application/octet-stream",
            "X-FoxForge-Filename": "job.gcode",
            "X-FoxForge-Sha256": digest,
            "X-Request-Id": "req-upload-1",
        },
    )
    assert response.status == 201
    body = await response.json()
    assert body["artifactId"] == digest
    assert body["replayed"] is False

    replay = await client.post(
        "/api/v1/artifacts",
        data=payload,
        headers={
            "Authorization": f"Bearer {_TOKEN}",
            "Content-Type": "application/octet-stream",
            "X-FoxForge-Filename": "job.gcode",
            "X-FoxForge-Sha256": digest,
            "X-Request-Id": "req-upload-2",
        },
    )
    assert replay.status == 200
    assert (await replay.json())["replayed"] is True
    return digest


def test_queue_commands_stage_enqueue_dispatch_and_replay_without_duplicate_start(tmp_path) -> None:
    async def scenario() -> None:
        app, fleet, queue, printing, audit = _build_app(tmp_path)
        client = TestClient(TestServer(app))
        await client.start_server()
        await fleet.connect("x2d-main")
        try:
            artifact_id = await _upload(client, b"; FoxForge\nG28\nG1 X10 Y10\n")
            enqueue_payload = {
                "queueId": _QUEUE_ID,
                "dispatchId": _DISPATCH_ID,
                "printerId": "x2d-main",
                "artifactId": artifact_id,
                "requestedName": "API queue test",
            }
            added = await client.post(
                "/api/v1/queue",
                json=enqueue_payload,
                headers=_command_headers("enqueue-1", "req-enqueue-1"),
            )
            assert added.status == 201
            assert (await added.json())["state"] == "pending"

            enqueue_replay = await client.post(
                "/api/v1/queue",
                json=enqueue_payload,
                headers=_command_headers("enqueue-1", "req-enqueue-replay"),
            )
            assert enqueue_replay.status == 200
            assert (await enqueue_replay.json())["replayed"] is True
            assert len(queue.list()) == 1

            changed_payload = dict(enqueue_payload)
            changed_payload["requestedName"] = "changed"
            changed = await client.post(
                "/api/v1/queue",
                json=changed_payload,
                headers=_command_headers("enqueue-1", "req-enqueue-conflict"),
            )
            assert changed.status == 409
            assert (await changed.json())["error"]["code"] == "idempotency_conflict"

            dispatched = await client.post(
                f"/api/v1/queue/{_QUEUE_ID}/dispatch",
                headers=_command_headers("dispatch-1", "req-dispatch-1"),
            )
            assert dispatched.status == 200
            dispatch_body = await dispatched.json()
            assert dispatch_body["state"] in {"accepted", "preparing"}
            assert printing.start_count == 1

            replay = await client.post(
                f"/api/v1/queue/{_QUEUE_ID}/dispatch",
                headers=_command_headers("dispatch-1", "req-dispatch-replay"),
            )
            assert replay.status == 200
            assert (await replay.json())["replayed"] is True
            assert printing.start_count == 1

            audit_records = audit.list_for_request("req-enqueue-1")
            assert [record.outcome for record in audit_records] == [
                CommandAuditOutcome.ACCEPTED,
                CommandAuditOutcome.COMPLETED,
            ]
            assert audit_records[0].principal_id == "operator"
            assert audit_records[0].action == "queue.enqueue"
            assert audit_records[0].idempotency_key_digest == command_idempotency_key_digest("enqueue-1")
            assert audit_records[0].idempotency_key_digest != "enqueue-1"
        finally:
            await queue.aclose()
            await fleet.aclose()
            await client.close()

    asyncio.run(scenario())


def test_indeterminate_dispatch_requires_reconciliation_and_replays_safely(tmp_path) -> None:
    async def scenario() -> None:
        app, fleet, queue, printing, _ = _build_app(tmp_path)
        client = TestClient(TestServer(app))
        await client.start_server()
        await fleet.connect("x2d-main")
        try:
            artifact_id = await _upload(client, b"; second job\nG28\n")
            enqueue_payload = {
                "queueId": _QUEUE_ID_2,
                "dispatchId": _DISPATCH_ID_2,
                "printerId": "x2d-main",
                "artifactId": artifact_id,
            }
            added = await client.post(
                "/api/v1/queue",
                json=enqueue_payload,
                headers=_command_headers("enqueue-2", "req-enqueue-2"),
            )
            assert added.status == 201

            printing.make_next_submit_indeterminate()
            uncertain = await client.post(
                f"/api/v1/queue/{_QUEUE_ID_2}/dispatch",
                headers=_command_headers("dispatch-2", "req-dispatch-2"),
            )
            assert uncertain.status == 200
            body = await uncertain.json()
            assert body["state"] == "indeterminate"
            assert body["reconciliationRequired"] is True
            assert printing.start_count == 1

            replay = await client.post(
                f"/api/v1/queue/{_QUEUE_ID_2}/dispatch",
                headers=_command_headers("dispatch-2", "req-dispatch-2-replay"),
            )
            assert replay.status == 200
            replay_body = await replay.json()
            assert replay_body["state"] == "indeterminate"
            assert replay_body["replayed"] is True
            assert printing.start_count == 1

            blocked_retry = await client.post(
                f"/api/v1/queue/{_QUEUE_ID_2}/dispatch",
                headers=_command_headers("dispatch-2-new-key", "req-dispatch-2-new"),
            )
            assert blocked_retry.status == 409
            assert (await blocked_retry.json())["error"]["code"] == "queue_reconciliation_required"
            assert printing.start_count == 1

            reconciled = await client.post(
                f"/api/v1/queue/{_QUEUE_ID_2}/reconcile",
                json={"accepted": False},
                headers=_command_headers("reconcile-2", "req-reconcile-2"),
            )
            assert reconciled.status == 200
            assert (await reconciled.json())["state"] == "pending"

            reconcile_replay = await client.post(
                f"/api/v1/queue/{_QUEUE_ID_2}/reconcile",
                json={"accepted": False},
                headers=_command_headers("reconcile-2", "req-reconcile-2-replay"),
            )
            assert reconcile_replay.status == 200
            assert (await reconcile_replay.json())["replayed"] is True
            assert queue.get(UUID(_QUEUE_ID_2)).state.value == "pending"
        finally:
            await queue.aclose()
            await fleet.aclose()
            await client.close()

    asyncio.run(scenario())


def test_queue_commands_fail_closed_and_audit_denied_requests(tmp_path) -> None:
    async def scenario() -> None:
        app, fleet, queue, _, audit = _build_app(tmp_path)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/artifacts",
                data=b"G28\n",
                headers={
                    "Content-Type": "application/octet-stream",
                    "X-FoxForge-Filename": "unauthorized.gcode",
                    "X-FoxForge-Sha256": hashlib.sha256(b"G28\n").hexdigest(),
                    "X-Request-Id": "req-denied-1",
                },
            )
            assert response.status == 401
            records = audit.list_for_request("req-denied-1")
            assert len(records) == 1
            assert records[0].outcome == CommandAuditOutcome.DENIED
            assert records[0].principal_id is None
            assert records[0].action == "artifact.stage"
        finally:
            await queue.aclose()
            await fleet.aclose()
            await client.close()

    asyncio.run(scenario())
