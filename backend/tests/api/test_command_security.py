# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1 import (
    BearerCommandSecurity,
    CommandPermission,
    add_command_route,
    command_principal,
    create_api_v1_app,
)
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueService

_TOKEN = "foxforge-command-token-0123456789abcdef"


def _app(token: str | None, permission: CommandPermission = CommandPermission.INVENTORY_WRITE) -> web.Application:
    fleet = FleetService([])
    app = create_api_v1_app(
        fleet=fleet,
        queue=QueueService(fleet, InMemoryQueueStore()),
        inventory=InventoryService(InMemoryInventoryStore()),
        command_security=BearerCommandSecurity(token),
    )

    async def command(request: web.Request) -> web.Response:
        principal = command_principal(request)
        return web.json_response(
            {
                "principalId": principal.principal_id,
                "permissions": sorted(item.value for item in principal.permissions),
            }
        )

    add_command_route(app, "POST", "/api/v1/test-command", permission, command)
    return app


def test_unconfigured_command_api_fails_closed_with_normalized_error() -> None:
    async def scenario() -> None:
        client = TestClient(TestServer(_app(None)))
        await client.start_server()
        try:
            response = await client.post("/api/v1/test-command", headers={"X-Request-Id": "client.req-001"})
            assert response.status == 503
            payload = await response.json()
            assert payload == {
                "error": {
                    "code": "command_api_disabled",
                    "message": "Command API is not enabled for this FoxForge runtime.",
                    "requestId": "client.req-001",
                    "retryable": False,
                }
            }
            assert response.headers["X-Request-Id"] == "client.req-001"
        finally:
            await client.close()

    asyncio.run(scenario())


def test_missing_or_invalid_bearer_token_is_unauthorized_without_secret_echo() -> None:
    async def scenario() -> None:
        client = TestClient(TestServer(_app(_TOKEN)))
        await client.start_server()
        try:
            missing = await client.post("/api/v1/test-command")
            assert missing.status == 401
            assert missing.headers["WWW-Authenticate"] == "Bearer"

            candidate = "wrong-command-token-0123456789abcdef"
            invalid = await client.post(
                "/api/v1/test-command",
                headers={"Authorization": f"Bearer {candidate}"},
            )
            assert invalid.status == 401
            payload = await invalid.json()
            assert payload["error"]["code"] == "unauthorized"
            assert candidate not in str(payload)
            assert _TOKEN not in str(payload)
        finally:
            await client.close()

    asyncio.run(scenario())


def test_valid_operator_token_resolves_non_admin_principal() -> None:
    async def scenario() -> None:
        client = TestClient(TestServer(_app(_TOKEN)))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/test-command",
                headers={"Authorization": f"Bearer {_TOKEN}"},
            )
            assert response.status == 200
            payload = await response.json()
            assert payload["principalId"] == "operator"
            assert payload["permissions"] == ["inventory.write", "printer.control", "queue.write"]
        finally:
            await client.close()

    asyncio.run(scenario())


def test_operator_token_does_not_implicitly_grant_admin_config() -> None:
    async def scenario() -> None:
        client = TestClient(TestServer(_app(_TOKEN, CommandPermission.ADMIN_CONFIG)))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/test-command",
                headers={"Authorization": f"Bearer {_TOKEN}"},
            )
            assert response.status == 403
            assert (await response.json())["error"]["code"] == "forbidden"
        finally:
            await client.close()

    asyncio.run(scenario())


def test_existing_read_endpoint_remains_available_and_gets_request_id() -> None:
    async def scenario() -> None:
        client = TestClient(TestServer(_app(None)))
        await client.start_server()
        try:
            response = await client.get("/healthz", headers={"X-Request-Id": "not valid because spaces"})
            assert response.status == 200
            assert await response.json() == {"status": "ok", "apiVersion": "1"}
            generated = response.headers["X-Request-Id"]
            UUID(generated)
        finally:
            await client.close()

    asyncio.run(scenario())


def test_command_token_requires_high_entropy_visible_ascii() -> None:
    with pytest.raises(ValueError):
        BearerCommandSecurity("too-short")
    with pytest.raises(ValueError):
        BearerCommandSecurity("a" * 31 + " ")
