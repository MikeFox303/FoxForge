# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
import hashlib
import io
import zipfile

from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1 import BearerCommandSecurity, create_api_v1_app
from foxforge.api.v1.artifact_reads import register_artifact_read_routes
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueService
from foxforge.domain.printers.capabilities import PrintArtifactFormat
from foxforge.infrastructure.artifacts import FilesystemArtifactStore

_TOKEN = "artifact-read-token-0123456789abcdef"


def _three_mf() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Metadata/plate_1.gcode", "M620 S0A\nM620 S1A\n")
    return buffer.getvalue()


async def _chunks(payload: bytes):
    yield payload


def test_print_plan_read_requires_operator_auth_and_returns_staged_plan(tmp_path) -> None:
    async def scenario() -> None:
        fleet = FleetService([])
        queue = QueueService(fleet, InMemoryQueueStore())
        artifacts = FilesystemArtifactStore(tmp_path / "artifacts")
        app = create_api_v1_app(
            fleet=fleet,
            queue=queue,
            inventory=InventoryService(InMemoryInventoryStore()),
            command_security=BearerCommandSecurity(_TOKEN),
        )
        register_artifact_read_routes(app, artifacts=artifacts)

        payload = _three_mf()
        digest = hashlib.sha256(payload).hexdigest()
        staged = await artifacts.stage(
            filename="safe-test.3mf",
            format=PrintArtifactFormat.THREE_MF,
            expected_sha256=digest,
            chunks=_chunks(payload),
            max_size_bytes=1024 * 1024,
        )
        assert staged.artifact.artifact_id == digest

        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            unauthorized = await client.get(f"/api/v1/artifacts/{digest}/print-plan")
            assert unauthorized.status == 401
            assert (await unauthorized.json())["error"]["code"] == "unauthorized"

            response = await client.get(
                f"/api/v1/artifacts/{digest}/print-plan",
                headers={"Authorization": f"Bearer {_TOKEN}", "X-Request-Id": "artifact-plan-read"},
            )
            assert response.status == 200
            body = await response.json()
            assert body["artifactId"] == digest
            assert body["artifactSha256"] == digest
            assert body["readyForRouting"] is True
            assert body["plates"] == [
                {
                    "plateIndex": 0,
                    "readyForRouting": True,
                    "materialRequirements": [
                        {
                            "materialIndex": 0,
                            "materialFamily": None,
                            "rgbaHex": None,
                            "profileName": None,
                            "expectedToolheadPosition": None,
                        },
                        {
                            "materialIndex": 1,
                            "materialFamily": None,
                            "rgbaHex": None,
                            "profileName": None,
                            "expectedToolheadPosition": None,
                        },
                    ],
                }
            ]
            assert body["issues"] == []
        finally:
            await client.close()
            await queue.aclose()
            await fleet.aclose()

    asyncio.run(scenario())


def test_print_plan_read_rejects_non_3mf_and_changed_staged_content(tmp_path) -> None:
    async def scenario() -> None:
        fleet = FleetService([])
        queue = QueueService(fleet, InMemoryQueueStore())
        artifacts = FilesystemArtifactStore(tmp_path / "artifacts")
        app = create_api_v1_app(
            fleet=fleet,
            queue=queue,
            inventory=InventoryService(InMemoryInventoryStore()),
            command_security=BearerCommandSecurity(_TOKEN),
        )
        register_artifact_read_routes(app, artifacts=artifacts)
        client = TestClient(TestServer(app))
        await client.start_server()
        headers = {"Authorization": f"Bearer {_TOKEN}"}
        try:
            gcode = b"G28\n"
            gcode_digest = hashlib.sha256(gcode).hexdigest()
            await artifacts.stage(
                filename="job.gcode",
                format=PrintArtifactFormat.GCODE,
                expected_sha256=gcode_digest,
                chunks=_chunks(gcode),
                max_size_bytes=1024,
            )
            unsupported = await client.get(f"/api/v1/artifacts/{gcode_digest}/print-plan", headers=headers)
            assert unsupported.status == 422
            assert (await unsupported.json())["error"]["code"] == "unsupported_artifact"

            payload = _three_mf()
            digest = hashlib.sha256(payload).hexdigest()
            staged = await artifacts.stage(
                filename="job.3mf",
                format=PrintArtifactFormat.THREE_MF,
                expected_sha256=digest,
                chunks=_chunks(payload),
                max_size_bytes=1024 * 1024,
            )
            staged.artifact.path.write_bytes(b"mutated")
            changed = await client.get(f"/api/v1/artifacts/{digest}/print-plan", headers=headers)
            assert changed.status == 404
            assert (await changed.json())["error"]["code"] == "artifact_not_found"
        finally:
            await client.close()
            await queue.aclose()
            await fleet.aclose()

    asyncio.run(scenario())


def test_print_plan_read_validates_artifact_id_before_store_lookup(tmp_path) -> None:
    async def scenario() -> None:
        fleet = FleetService([])
        queue = QueueService(fleet, InMemoryQueueStore())
        artifacts = FilesystemArtifactStore(tmp_path / "artifacts")
        app = create_api_v1_app(
            fleet=fleet,
            queue=queue,
            inventory=InventoryService(InMemoryInventoryStore()),
            command_security=BearerCommandSecurity(_TOKEN),
        )
        register_artifact_read_routes(app, artifacts=artifacts)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get(
                "/api/v1/artifacts/not-a-digest/print-plan",
                headers={"Authorization": f"Bearer {_TOKEN}"},
            )
            assert response.status == 400
            assert (await response.json())["error"]["code"] == "invalid_request"
        finally:
            await client.close()
            await queue.aclose()
            await fleet.aclose()

    asyncio.run(scenario())
