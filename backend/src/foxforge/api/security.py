# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hmac
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4

from aiohttp import web


class CommandPermission(StrEnum):
    QUEUE_WRITE = "queue.write"
    PRINTER_CONTROL = "printer.control"
    INVENTORY_WRITE = "inventory.write"
    ADMIN_CONFIG = "admin.config"


@dataclass(frozen=True, slots=True)
class CommandPrincipal:
    principal_id: str
    permissions: frozenset[CommandPermission]

    def __post_init__(self) -> None:
        if not self.principal_id.strip():
            raise ValueError("principal_id must not be empty")

    def allows(self, permission: CommandPermission) -> bool:
        return permission in self.permissions


class CommandSecurityError(RuntimeError):
    status: int
    code: str
    message: str
    retryable: bool

    def __init__(self, *, status: int, code: str, message: str, retryable: bool = False) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class CommandApiDisabledError(CommandSecurityError):
    def __init__(self) -> None:
        super().__init__(
            status=503,
            code="command_api_disabled",
            message="FoxForge command API is disabled for this deployment.",
        )


class CommandUnauthorizedError(CommandSecurityError):
    def __init__(self) -> None:
        super().__init__(status=401, code="unauthorized", message="Valid Bearer authentication is required.")


class CommandForbiddenError(CommandSecurityError):
    def __init__(self) -> None:
        super().__init__(
            status=403,
            code="forbidden",
            message="The authenticated principal is not permitted to run this command.",
        )


class BearerCommandAuthenticator:
    """Resolve the deployment-supplied alpha command token to a FoxForge principal."""

    def __init__(self, token: str | None) -> None:
        cleaned = token.strip() if isinstance(token, str) else ""
        self._token = cleaned or None
        self._principal = CommandPrincipal(
            principal_id="static-operator",
            permissions=frozenset(
                {
                    CommandPermission.QUEUE_WRITE,
                    CommandPermission.PRINTER_CONTROL,
                    CommandPermission.INVENTORY_WRITE,
                }
            ),
        )

    @property
    def enabled(self) -> bool:
        return self._token is not None

    def authenticate(self, authorization: str | None) -> CommandPrincipal:
        if self._token is None:
            raise CommandApiDisabledError
        candidate = _bearer_credential(authorization)
        if candidate is None or not hmac.compare_digest(candidate.encode("utf-8"), self._token.encode("utf-8")):
            raise CommandUnauthorizedError
        return self._principal

    @staticmethod
    def require(principal: CommandPrincipal, permission: CommandPermission) -> None:
        if not principal.allows(permission):
            raise CommandForbiddenError

    def __repr__(self) -> str:
        return f"BearerCommandAuthenticator(enabled={self.enabled!r})"


def resolve_request_id(value: str | None) -> UUID:
    if isinstance(value, str):
        candidate = value.strip()
        if candidate:
            try:
                return UUID(candidate)
            except ValueError:
                pass
    return uuid4()


def command_error_response(error: CommandSecurityError, *, request_id: UUID) -> web.Response:
    response = web.json_response(
        {
            "error": {
                "code": error.code,
                "message": error.message,
                "requestId": str(request_id),
                "retryable": error.retryable,
            }
        },
        status=error.status,
    )
    response.headers["X-Request-Id"] = str(request_id)
    if isinstance(error, CommandUnauthorizedError):
        response.headers["WWW-Authenticate"] = "Bearer"
    return response


def _bearer_credential(authorization: str | None) -> str | None:
    if not isinstance(authorization, str):
        return None
    scheme, separator, credential = authorization.strip().partition(" ")
    if not separator or scheme.lower() != "bearer":
        return None
    cleaned = credential.strip()
    return cleaned or None
