# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hmac
import json
from uuid import UUID, uuid4

import pytest

from foxforge.api.security import (
    BearerCommandAuthenticator,
    CommandApiDisabledError,
    CommandForbiddenError,
    CommandPermission,
    CommandUnauthorizedError,
    command_error_response,
    resolve_request_id,
)


def test_command_authenticator_fails_closed_when_token_is_unset() -> None:
    authenticator = BearerCommandAuthenticator(None)

    assert authenticator.enabled is False
    with pytest.raises(CommandApiDisabledError):
        authenticator.authenticate("Bearer anything")


def test_command_authenticator_accepts_only_matching_bearer_token(monkeypatch) -> None:
    calls: list[tuple[bytes, bytes]] = []
    real_compare = hmac.compare_digest

    def compare(left: bytes, right: bytes) -> bool:
        calls.append((left, right))
        return real_compare(left, right)

    monkeypatch.setattr(hmac, "compare_digest", compare)
    authenticator = BearerCommandAuthenticator("very-secret-token")

    principal = authenticator.authenticate("Bearer very-secret-token")

    assert principal.principal_id == "static-operator"
    assert principal.allows(CommandPermission.QUEUE_WRITE)
    assert principal.allows(CommandPermission.PRINTER_CONTROL)
    assert principal.allows(CommandPermission.INVENTORY_WRITE)
    assert not principal.allows(CommandPermission.ADMIN_CONFIG)
    assert calls == [(b"very-secret-token", b"very-secret-token")]
    assert "very-secret-token" not in repr(authenticator)

    for header in (None, "", "Basic very-secret-token", "Bearer wrong-token"):
        with pytest.raises(CommandUnauthorizedError):
            authenticator.authenticate(header)


def test_command_permission_check_is_explicit() -> None:
    authenticator = BearerCommandAuthenticator("very-secret-token")
    principal = authenticator.authenticate("Bearer very-secret-token")

    authenticator.require(principal, CommandPermission.INVENTORY_WRITE)
    with pytest.raises(CommandForbiddenError):
        authenticator.require(principal, CommandPermission.ADMIN_CONFIG)


def test_request_id_preserves_valid_uuid_and_replaces_invalid_value() -> None:
    request_id = uuid4()

    assert resolve_request_id(str(request_id)) == request_id
    assert isinstance(resolve_request_id("not-a-uuid"), UUID)
    assert isinstance(resolve_request_id(None), UUID)


def test_command_error_response_uses_normalized_envelope() -> None:
    request_id = uuid4()
    response = command_error_response(CommandUnauthorizedError(), request_id=request_id)

    assert response.status == 401
    assert response.headers["X-Request-Id"] == str(request_id)
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert json.loads(response.text) == {
        "error": {
            "code": "unauthorized",
            "message": "Valid Bearer authentication is required.",
            "requestId": str(request_id),
            "retryable": False,
        }
    }
