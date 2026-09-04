# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hmac
from dataclasses import dataclass
from enum import StrEnum


class CommandPermission(StrEnum):
    QUEUE_WRITE = "queue.write"
    PRINTER_CONTROL = "printer.control"
    INVENTORY_WRITE = "inventory.write"
    ADMIN_CONFIG = "admin.config"


@dataclass(frozen=True, slots=True)
class CommandPrincipal:
    principal_id: str
    permissions: frozenset[CommandPermission]

    def allows(self, permission: CommandPermission) -> bool:
        return permission in self.permissions


class CommandSecurityDisabledError(RuntimeError):
    pass


class CommandAuthenticationError(RuntimeError):
    pass


class BearerCommandSecurity:
    """Fail-closed command authentication for the first remote-write phase."""

    _OPERATOR_PERMISSIONS = frozenset(
        {
            CommandPermission.QUEUE_WRITE,
            CommandPermission.PRINTER_CONTROL,
            CommandPermission.INVENTORY_WRITE,
        }
    )

    def __init__(self, token: str | None) -> None:
        if token == "":
            token = None
        if token is not None:
            _validate_token(token)
        self._token = token

    @property
    def enabled(self) -> bool:
        return self._token is not None

    def authenticate(self, authorization_header: str | None) -> CommandPrincipal:
        token = self._token
        if token is None:
            raise CommandSecurityDisabledError("command API is disabled")
        if authorization_header is None:
            raise CommandAuthenticationError("command credentials are required")

        scheme, separator, candidate = authorization_header.partition(" ")
        if (
            separator != " "
            or scheme.lower() != "bearer"
            or not candidate
            or any(character.isspace() for character in candidate)
        ):
            raise CommandAuthenticationError("command credentials are invalid")
        if not hmac.compare_digest(candidate, token):
            raise CommandAuthenticationError("command credentials are invalid")

        return CommandPrincipal(
            principal_id="operator",
            permissions=self._OPERATOR_PERMISSIONS,
        )


def _validate_token(token: str) -> None:
    if not 32 <= len(token) <= 512:
        raise ValueError("FOXFORGE_COMMAND_TOKEN must contain 32 to 512 visible ASCII characters")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in token):
        raise ValueError("FOXFORGE_COMMAND_TOKEN must contain visible ASCII characters only")
