# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio
from uuid import UUID

from aiohttp import web

from foxforge.application.commands import (
    CommandIdempotencyState,
    CommandIdempotencyStore,
    command_request_fingerprint,
)
from foxforge.application.queue import QueueEntryNotFoundError, QueueEntryState, QueueService

from .http import command_error
from .read_models import _queue_entry
from .security import (
    BearerCommandSecurity,
    CommandAuthenticationError,
    CommandSecurityDisabledError,
)


def install_queue_command_guard(
    app: web.Application,
    *,
    queue: QueueService,
    security: BearerCommandSecurity,
    idempotency: CommandIdempotencyStore,
) -> None:
    """Serialize queue side-effect commands and resolve safe HTTP replays.

    QueueService already persists DISPATCHING before printer submission. This
    middleware adds the single-process HTTP critical section needed to stop two
    concurrent authenticated requests from racing that boundary, and it checks
    completed HTTP idempotency records before current queue state so a replay of
    an INDETERMINATE dispatch returns the same logical resource instead of being
    mistaken for a new blind retry.
    """

    command_lock = asyncio.Lock()

    @web.middleware
    async def queue_guard(request: web.Request, handler):
        operation = _operation(request.method, request.path)
        if operation is None:
            return await handler(request)

        async with command_lock:
            replay = await _replay_if_known(
                request,
                queue=queue,
                security=security,
                idempotency=idempotency,
                operation=operation,
            )
            if replay is not None:
                return replay
            return await handler(request)

    app.middlewares.append(queue_guard)


async def _replay_if_known(
    request: web.Request,
    *,
    queue: QueueService,
    security: BearerCommandSecurity,
    idempotency: CommandIdempotencyStore,
    operation: str,
) -> web.Response | None:
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key:
        return None
    try:
        principal = security.authenticate(request.headers.get("Authorization"))
    except (CommandAuthenticationError, CommandSecurityDisabledError):
        return None

    queue_id_text = _queue_id_from_path(request.path)
    try:
        queue_id = UUID(queue_id_text)
    except ValueError:
        return None

    payload: object
    if operation == "queue.dispatch":
        payload = {}
    else:
        if request.content_type != "application/json":
            return None
        try:
            payload = await request.json()
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None

    fingerprint = command_request_fingerprint(
        {"routeIdentity": str(queue_id), "payload": payload}
    )
    record = idempotency.get(principal.principal_id, operation, key)
    if record is None:
        return None
    if record.request_fingerprint != fingerprint:
        return command_error(
            request,
            status=409,
            code="idempotency_conflict",
            message="idempotency key was already used with a different request",
        )
    if record.state != CommandIdempotencyState.COMPLETED:
        return command_error(
            request,
            status=409,
            code="reconciliation_required",
            message="A previous command with this idempotency key is still unresolved.",
        )

    try:
        entry = queue.get(queue_id)
    except QueueEntryNotFoundError:
        return command_error(
            request,
            status=409,
            code="reconciliation_required",
            message="The previous command completed but its queue resource cannot be found.",
        )

    result = _queue_entry(entry)
    result["replayed"] = True
    if operation == "queue.dispatch":
        result["reconciliationRequired"] = entry.state == QueueEntryState.INDETERMINATE
    return web.json_response(result)


def _operation(method: str, path: str) -> str | None:
    if method.upper() != "POST":
        return None
    if path.startswith("/api/v1/queue/") and path.endswith("/dispatch"):
        return "queue.dispatch"
    if path.startswith("/api/v1/queue/") and path.endswith("/reconcile"):
        return "queue.reconcile"
    return None


def _queue_id_from_path(path: str) -> str:
    parts = path.split("/")
    return parts[4] if len(parts) >= 6 else ""
