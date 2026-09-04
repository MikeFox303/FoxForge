# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class CommandPermission(StrEnum):
    QUEUE_WRITE = "queue.write"
    PRINTER_CONTROL = "printer.control"
    PRINTER_CONFIG = "printer.config"
    INVENTORY_WRITE = "inventory.write"
    ADMIN_CONFIG = "admin.config"


@dataclass(frozen=True, slots=True)
class CommandPrincipal:
    principal_id: str
    permissions: frozenset[CommandPermission]

    def allows(self, permission: CommandPermission) -> bool:
        return permission in self.permissions


@dataclass(frozen=True, slots=True)
class BrowserCommandSession:
    access_token: str
    expires_at: datetime


class CommandSecurityDisabledError(RuntimeError):
    pass


class CommandAuthenticationError(RuntimeError):
    pass


class TrustedBrowserCommandSessions:
    """Short-lived in-memory browser credentials.

    Session issuance is intentionally separate from bootstrap authorization.
    `BearerCommandSecurity` decides whether a static operator token or a trusted
    proxy assertion is allowed to mint a session.
    """

    def __init__(self, *, enabled: bool = False, ttl_seconds: int = 8 * 60 * 60) -> None:
        if ttl_seconds <= 0:
            raise ValueError("browser command session ttl_seconds must be positive")
        self._enabled = enabled
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, float] = {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    def issue(self) -> BrowserCommandSession:
        if not self._enabled:
            raise CommandSecurityDisabledError("browser command sessions are disabled")
        self._prune()
        token = secrets.token_urlsafe(32)
        self._sessions[_token_digest(token)] = time.monotonic() + self._ttl_seconds
        return BrowserCommandSession(
            access_token=token,
            expires_at=datetime.now(UTC) + timedelta(seconds=self._ttl_seconds),
        )

    def accepts(self, token: str) -> bool:
        if not self._enabled:
            return False
        self._prune()
        deadline = self._sessions.get(_token_digest(token))
        return deadline is not None and deadline > time.monotonic()

    def _prune(self) -> None:
        now = time.monotonic()
        expired = [digest for digest, deadline in self._sessions.items() if deadline <= now]
        for digest in expired:
            self._sessions.pop(digest, None)


class BearerCommandSecurity:
    """Fail-closed command authentication for API and browser clients."""

    _OPERATOR_PERMISSIONS = frozenset(
        {
            CommandPermission.QUEUE_WRITE,
            CommandPermission.PRINTER_CONTROL,
            CommandPermission.PRINTER_CONFIG,
            CommandPermission.INVENTORY_WRITE,
        }
    )

    def __init__(
        self,
        token: str | None,
        *,
        browser_sessions: TrustedBrowserCommandSessions | None = None,
        trusted_proxy_secret: str | None = None,
    ) -> None:
        if token == "":
            token = None
        if trusted_proxy_secret == "":
            trusted_proxy_secret = None
        if token is not None:
            _validate_secret(token, field_name="FOXFORGE_COMMAND_TOKEN")
        if trusted_proxy_secret is not None:
            _validate_secret(trusted_proxy_secret, field_name="FOXFORGE_TRUSTED_PROXY_SECRET")
            if browser_sessions is None or not browser_sessions.enabled:
                raise ValueError("trusted proxy bootstrap requires browser sessions to be enabled")
        self._token = token
        self._browser_sessions = browser_sessions
        self._trusted_proxy_secret = trusted_proxy_secret

    @property
    def enabled(self) -> bool:
        return self._token is not None or bool(self._browser_sessions and self._browser_sessions.enabled)

    @property
    def operator_token_configured(self) -> bool:
        return self._token is not None

    @property
    def browser_sessions_enabled(self) -> bool:
        return bool(self._browser_sessions and self._browser_sessions.enabled)

    @property
    def trusted_proxy_bootstrap_enabled(self) -> bool:
        return self._trusted_proxy_secret is not None

    def issue_browser_session(
        self,
        *,
        authorization_header: str | None = None,
        trusted_proxy_assertion: str | None = None,
    ) -> BrowserCommandSession:
        sessions = self._browser_sessions
        if sessions is None or not sessions.enabled:
            raise CommandSecurityDisabledError("browser command sessions are disabled")

        if authorization_header is not None:
            candidate = _bearer_candidate(authorization_header)
            if self._token is not None and hmac.compare_digest(candidate, self._token):
                return sessions.issue()
            raise CommandAuthenticationError("operator bootstrap credential is invalid")

        if self._trusted_proxy_secret is not None and trusted_proxy_assertion is not None:
            if hmac.compare_digest(trusted_proxy_assertion, self._trusted_proxy_secret):
                return sessions.issue()
            raise CommandAuthenticationError("trusted proxy assertion is invalid")

        raise CommandAuthenticationError("browser session bootstrap credentials are required")

    def authenticate(self, authorization_header: str | None) -> CommandPrincipal:
        if not self.enabled:
            raise CommandSecurityDisabledError("command API is disabled")
        if authorization_header is None:
            raise CommandAuthenticationError("command credentials are required")

        candidate = _bearer_candidate(authorization_header)
        static_match = self._token is not None and hmac.compare_digest(candidate, self._token)
        browser_match = self._browser_sessions is not None and self._browser_sessions.accepts(candidate)
        if not static_match and not browser_match:
            raise CommandAuthenticationError("command credentials are invalid")

        return CommandPrincipal(principal_id="operator", permissions=self._OPERATOR_PERMISSIONS)


def _bearer_candidate(authorization_header: str) -> str:
    scheme, separator, candidate = authorization_header.partition(" ")
    if (
        separator != " "
        or scheme.lower() != "bearer"
        or not candidate
        or any(character.isspace() for character in candidate)
    ):
        raise CommandAuthenticationError("command credentials are invalid")
    return candidate


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _validate_secret(secret: str, *, field_name: str) -> None:
    if not 32 <= len(secret) <= 512:
        raise ValueError(f"{field_name} must contain 32 to 512 visible ASCII characters")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in secret):
        raise ValueError(f"{field_name} must contain visible ASCII characters only")
