# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import uuid4

from aiohttp import web

from foxforge.application.commands import (
    CommandIdempotencyConflictError,
    CommandIdempotencyRecord,
    CommandIdempotencyState,
    CommandIdempotencyStore,
    command_request_fingerprint,
)
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InventoryService
from foxforge.application.printer_management import (
    PrinterConfiguration,
    PrinterConfigurationConflictError,
    PrinterConfigurationNotFoundError,
    PrinterConnectionValidationError,
    PrinterManagementService,
    PrinterSetupOutcome,
)
from foxforge.application.queue import QueueService
from foxforge.domain.printers import PrinterAdapterError, PrinterErrorCode, PrinterIdentity

from .read_models import API_VERSION, fleet_read_model, inventory_read_model, queue_read_model
from .security import (
    BearerCommandSecurity,
    CommandAuthenticationError,
    CommandPermission,
    CommandPrincipal,
    CommandSecurityDisabledError,
)

_JSON_HANDLER = Callable[[web.Request], Awaitable[web.StreamResponse]]
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_PRINTER_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_CONNECTION_FAILURE_OUTCOME = "printer_connection_failed"

_REQUEST_ID_KEY = web.RequestKey("foxforge_request_id", str)
_COMMAND_SECURITY_KEY = web.AppKey("foxforge_command_security", BearerCommandSecurity)
_COMMAND_PRINCIPAL_KEY = web.RequestKey("foxforge_command_principal", CommandPrincipal)
_COMMAND_IDEMPOTENCY_KEY = web.AppKey("foxforge_command_idempotency", CommandIdempotencyStore)


def create_api_v1_app(
    *,
    fleet: FleetService,
    queue: QueueService,
    inventory: InventoryService,
    command_security: BearerCommandSecurity | None = None,
    command_idempotency: CommandIdempotencyStore | None = None,
    printer_management: PrinterManagementService | None = None,
) -> web.Application:
    """Create FoxForge HTTP API v1 with reads plus explicitly guarded mutations."""

    app = web.Application(middlewares=[_request_context, _response_headers])
    app[_COMMAND_SECURITY_KEY] = command_security or BearerCommandSecurity(None)
    if command_idempotency is not None:
        app[_COMMAND_IDEMPOTENCY_KEY] = command_idempotency

    async def healthz(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "apiVersion": API_VERSION})

    async def fleet_snapshot(_: web.Request) -> web.Response:
        return web.json_response(fleet_read_model(fleet))

    async def queue_snapshot(_: web.Request) -> web.Response:
        return web.json_response(queue_read_model(queue))

    async def inventory_spools(_: web.Request) -> web.Response:
        return web.json_response(inventory_read_model(inventory))

    async def operator_session(request: web.Request) -> web.Response:
        security = request.app[_COMMAND_SECURITY_KEY]
        try:
            session = security.issue_browser_session()
        except CommandSecurityDisabledError:
            return command_error(
                request,
                status=503,
                code="browser_session_disabled",
                message="Trusted browser command sessions are not enabled for this deployment.",
            )
        return web.json_response(
            {
                "accessToken": session.access_token,
                "tokenType": "Bearer",
                "expiresAt": _datetime(session.expires_at),
            }
        )

    _add_get(app, "/healthz", healthz)
    _add_get(app, "/api/v1/fleet", fleet_snapshot)
    _add_get(app, "/api/v1/queue", queue_snapshot)
    _add_get(app, "/api/v1/inventory/spools", inventory_spools)
    app.router.add_post("/api/v1/operator-session", operator_session)

    if printer_management is not None:
        _register_printer_management_routes(app, printer_management)
    return app


def add_authenticated_route(
    app: web.Application,
    method: str,
    path: str,
    permission: CommandPermission,
    handler: _JSON_HANDLER,
) -> None:
    """Register one authenticated API route with an explicit permission."""

    async def guarded(request: web.Request) -> web.StreamResponse:
        security = request.app[_COMMAND_SECURITY_KEY]
        try:
            principal = security.authenticate(request.headers.get("Authorization"))
        except CommandSecurityDisabledError:
            return command_error(
                request,
                status=503,
                code="command_api_disabled",
                message="Command API is not enabled for this FoxForge runtime.",
            )
        except CommandAuthenticationError:
            response = command_error(
                request,
                status=401,
                code="unauthorized",
                message="Valid command credentials are required.",
            )
            response.headers["WWW-Authenticate"] = "Bearer"
            return response

        if not principal.allows(permission):
            return command_error(
                request,
                status=403,
                code="forbidden",
                message="The authenticated principal is not permitted to perform this command.",
            )

        request[_COMMAND_PRINCIPAL_KEY] = principal
        return await handler(request)

    app.router.add_route(method.upper(), path, guarded)


def add_command_route(
    app: web.Application,
    method: str,
    path: str,
    permission: CommandPermission,
    handler: _JSON_HANDLER,
) -> None:
    """Register one state-changing route behind ADR 0004 authentication."""

    normalized_method = method.upper()
    if normalized_method in {"GET", "HEAD", "OPTIONS"}:
        raise ValueError("command routes must use a state-changing HTTP method")
    add_authenticated_route(app, normalized_method, path, permission, handler)


def command_principal(request: web.Request) -> CommandPrincipal:
    principal = request.get(_COMMAND_PRINCIPAL_KEY)
    if principal is None:
        raise RuntimeError("command principal is unavailable outside an authenticated command handler")
    return principal


def command_idempotency_store(request: web.Request) -> CommandIdempotencyStore:
    store = request.app.get(_COMMAND_IDEMPOTENCY_KEY)
    if store is None:
        raise RuntimeError("durable command idempotency store is not configured")
    return store


def command_error(
    request: web.Request,
    *,
    status: int,
    code: str,
    message: str,
    retryable: bool = False,
) -> web.Response:
    return web.json_response(
        {
            "error": {
                "code": code,
                "message": message,
                "requestId": request[_REQUEST_ID_KEY],
                "retryable": retryable,
            }
        },
        status=status,
    )


def _register_printer_management_routes(app: web.Application, manager: PrinterManagementService) -> None:
    async def configurations(_: web.Request) -> web.Response:
        return web.json_response(
            {
                "apiVersion": API_VERSION,
                "printers": [_configuration_read_model(item) for item in manager.configurations()],
            }
        )

    async def test_connection(request: web.Request) -> web.Response:
        try:
            payload = await _json_object(request)
            configuration = _parse_printer_configuration(payload)
            outcome = await manager.test_connection(configuration)
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))
        return web.json_response(_setup_outcome(outcome))

    async def add_printer(request: web.Request) -> web.Response:
        try:
            payload = await _json_object(request)
            configuration = _parse_printer_configuration(payload)
            reservation = _reserve(request, "printer.add", payload)
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            failure_replay = _replay_connection_failure(request, reservation.record)
            if failure_replay is not None:
                return failure_replay
            replay = _replay_existing_configuration(request, manager, configuration, reservation.record.state)
            if replay is not None:
                return replay
            return command_error(
                request,
                status=409,
                code="reconciliation_required",
                message="A previous add-printer command with this idempotency key is unresolved.",
            )

        try:
            outcome = await manager.add(configuration)
        except PrinterConfigurationConflictError as error:
            return command_error(request, status=409, code="printer_exists", message=str(error))
        except PrinterConnectionValidationError as error:
            code, message = _public_connection_error(error.error)
            _complete_connection_failure(
                request,
                "printer.add",
                payload,
                code=code,
                retryable=error.error.retryable,
            )
            return command_error(
                request,
                status=422,
                code=code,
                message=message,
                retryable=error.error.retryable,
            )
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        _complete(request, "printer.add", payload, result_ref=configuration.identity.printer_id)
        return web.json_response(_setup_outcome(outcome), status=201)

    async def update_printer(request: web.Request) -> web.Response:
        printer_id = request.match_info["printer_id"]
        try:
            payload = await _json_object(request)
            configuration = _parse_printer_configuration(payload, route_printer_id=printer_id)
            reservation = _reserve(request, "printer.update", payload)
        except CommandIdempotencyConflictError as error:
            return command_error(request, status=409, code="idempotency_conflict", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        if not reservation.created:
            failure_replay = _replay_connection_failure(request, reservation.record)
            if failure_replay is not None:
                return failure_replay
            replay = _replay_existing_configuration(request, manager, configuration, reservation.record.state)
            if replay is not None:
                return replay
            return command_error(
                request,
                status=409,
                code="reconciliation_required",
                message="A previous update-printer command with this idempotency key is unresolved.",
            )

        try:
            outcome = await manager.update(printer_id, configuration)
        except PrinterConfigurationNotFoundError:
            return command_error(request, status=404, code="printer_not_found", message="Printer is not configured.")
        except PrinterConnectionValidationError as error:
            code, message = _public_connection_error(error.error)
            _complete_connection_failure(
                request,
                "printer.update",
                payload,
                code=code,
                retryable=error.error.retryable,
            )
            return command_error(
                request,
                status=422,
                code=code,
                message=message,
                retryable=error.error.retryable,
            )
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        _complete(request, "printer.update", payload, result_ref=printer_id)
        return web.json_response(_setup_outcome(outcome))

    async def remove_printer(request: web.Request) -> web.Response:
        printer_id = request.match_info["printer_id"]
        payload = {"printerId": printer_id}
        try:
            reservation = _reserve(request, "printer.remove", payload)
        except (CommandIdempotencyConflictError, ValueError) as error:
            status = 409 if isinstance(error, CommandIdempotencyConflictError) else 400
            return command_error(request, status=status, code="idempotency_conflict", message=str(error))

        if not reservation.created:
            try:
                manager.configuration(printer_id)
            except PrinterConfigurationNotFoundError:
                _complete(request, "printer.remove", payload, result_ref=printer_id)
                return web.json_response({"printerId": printer_id, "removed": True})
            if reservation.record.state == CommandIdempotencyState.COMPLETED:
                return web.json_response({"printerId": printer_id, "removed": True})
            return command_error(
                request,
                status=409,
                code="reconciliation_required",
                message="A previous remove-printer command with this idempotency key is unresolved.",
            )

        try:
            await manager.remove(printer_id)
        except PrinterConfigurationNotFoundError:
            return command_error(request, status=404, code="printer_not_found", message="Printer is not configured.")
        _complete(request, "printer.remove", payload, result_ref=printer_id)
        return web.json_response({"printerId": printer_id, "removed": True})

    async def reconnect(request: web.Request) -> web.Response:
        printer_id = request.match_info["printer_id"]
        try:
            outcome = await manager.reconnect(printer_id)
        except PrinterConfigurationNotFoundError:
            return command_error(request, status=404, code="printer_not_found", message="Printer is not configured.")
        return web.json_response(_setup_outcome(outcome))

    add_authenticated_route(
        app,
        "GET",
        "/api/v1/printers/configuration",
        CommandPermission.PRINTER_CONFIG,
        configurations,
    )
    add_command_route(
        app,
        "POST",
        "/api/v1/printers/test-connection",
        CommandPermission.PRINTER_CONFIG,
        test_connection,
    )
    add_command_route(app, "POST", "/api/v1/printers", CommandPermission.PRINTER_CONFIG, add_printer)
    add_command_route(
        app,
        "PUT",
        "/api/v1/printers/{printer_id}",
        CommandPermission.PRINTER_CONFIG,
        update_printer,
    )
    add_command_route(
        app,
        "DELETE",
        "/api/v1/printers/{printer_id}",
        CommandPermission.PRINTER_CONFIG,
        remove_printer,
    )
    add_command_route(
        app,
        "POST",
        "/api/v1/printers/{printer_id}/reconnect",
        CommandPermission.PRINTER_CONFIG,
        reconnect,
    )


def _reserve(request: web.Request, operation: str, payload: object):
    key = request.headers.get("Idempotency-Key", "")
    principal = command_principal(request)
    now = datetime.now(UTC)
    record = CommandIdempotencyRecord(
        principal_id=principal.principal_id,
        operation=operation,
        idempotency_key=key,
        request_fingerprint=command_request_fingerprint(payload),
        state=CommandIdempotencyState.STARTED,
        created_at=now,
        updated_at=now,
    )
    return command_idempotency_store(request).reserve(record)


def _complete(request: web.Request, operation: str, payload: object, *, result_ref: str) -> None:
    key = request.headers.get("Idempotency-Key", "")
    principal = command_principal(request)
    command_idempotency_store(request).complete(
        principal_id=principal.principal_id,
        operation=operation,
        idempotency_key=key,
        request_fingerprint=command_request_fingerprint(payload),
        outcome_code="completed",
        result_ref=result_ref,
    )


def _complete_connection_failure(
    request: web.Request,
    operation: str,
    payload: object,
    *,
    code: str,
    retryable: bool,
) -> None:
    key = request.headers.get("Idempotency-Key", "")
    principal = command_principal(request)
    command_idempotency_store(request).complete(
        principal_id=principal.principal_id,
        operation=operation,
        idempotency_key=key,
        request_fingerprint=command_request_fingerprint(payload),
        outcome_code=_CONNECTION_FAILURE_OUTCOME,
        result_ref=f"{code}|{1 if retryable else 0}",
    )


def _replay_connection_failure(
    request: web.Request,
    record: CommandIdempotencyRecord,
) -> web.Response | None:
    if record.state != CommandIdempotencyState.COMPLETED:
        return None
    if record.outcome_code != _CONNECTION_FAILURE_OUTCOME or record.result_ref is None:
        return None
    try:
        code, retryable_raw = record.result_ref.rsplit("|", 1)
    except ValueError:
        return None
    if retryable_raw not in {"0", "1"}:
        return None
    message = _public_connection_message(code)
    if message is None:
        return None
    return command_error(
        request,
        status=422,
        code=code,
        message=message,
        retryable=retryable_raw == "1",
    )


def _replay_existing_configuration(
    request: web.Request,
    manager: PrinterManagementService,
    expected: PrinterConfiguration,
    state: CommandIdempotencyState,
) -> web.Response | None:
    try:
        current = manager.configuration(expected.identity.printer_id)
    except PrinterConfigurationNotFoundError:
        return None
    if current != expected:
        return None
    if state != CommandIdempotencyState.COMPLETED:
        return None
    return web.json_response(
        {
            "configuration": _configuration_read_model(current),
            "replayed": True,
        }
    )


async def _json_object(request: web.Request) -> dict[str, object]:
    try:
        payload = await request.json()
    except Exception as error:
        raise ValueError("request body must be valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


def _parse_printer_configuration(
    payload: dict[str, object],
    *,
    route_printer_id: str | None = None,
) -> PrinterConfiguration:
    printer_id = _required_text(payload, "printerId")
    if not _PRINTER_ID_RE.fullmatch(printer_id):
        raise ValueError("printerId may contain only letters, digits, dot, underscore and hyphen")
    if route_printer_id is not None and route_printer_id != printer_id:
        raise ValueError("printerId must match the route")

    display_name = _required_text(payload, "displayName")
    kind = _required_text(payload, "kind").lower()
    model = _optional_text(payload.get("model"))
    vendor = _optional_text(payload.get("vendor"))
    connection = payload.get("connection")
    if not isinstance(connection, dict):
        raise ValueError("connection must be an object")

    if kind == "bambu":
        serial = _required_text(payload, "serialNumber")
        settings: dict[str, object] = {
            "host": _required_text(connection, "host"),
            "access_code": _required_text(connection, "accessCode"),
        }
        identity = PrinterIdentity(
            printer_id=printer_id,
            display_name=display_name,
            vendor=vendor or "bambu_lab",
            model=model,
            serial_number=serial,
            adapter_kind="bambu",
        )
    elif kind == "moonraker":
        base_url = _moonraker_url(_required_text(connection, "baseUrl"))
        api_key = _optional_text(connection.get("apiKey"))
        settings = {"base_url": base_url}
        if api_key is not None:
            settings["api_key"] = api_key
        identity = PrinterIdentity(
            printer_id=printer_id,
            display_name=display_name,
            vendor=vendor or "klipper",
            model=model,
            serial_number=_optional_text(payload.get("serialNumber")),
            adapter_kind="moonraker",
        )
    else:
        raise ValueError("kind must be 'bambu' or 'moonraker'")

    return PrinterConfiguration(identity=identity, settings=settings)


def _configuration_read_model(configuration: PrinterConfiguration) -> dict[str, object]:
    identity = configuration.identity
    if identity.adapter_kind == "bambu":
        connection: dict[str, object] = {
            "host": str(configuration.settings.get("host", "")),
            "accessCodeConfigured": bool(configuration.settings.get("access_code")),
        }
        kind = "bambu"
    else:
        connection = {
            "baseUrl": str(configuration.settings.get("base_url", "")),
            "apiKeyConfigured": bool(configuration.settings.get("api_key")),
        }
        kind = "moonraker"
    return {
        "printerId": identity.printer_id,
        "displayName": identity.display_name,
        "vendor": identity.vendor,
        "model": identity.model,
        "serialNumber": identity.serial_number,
        "kind": kind,
        "connection": connection,
    }


def _setup_outcome(outcome: PrinterSetupOutcome) -> dict[str, object]:
    error = outcome.connection_error
    public_message = _public_connection_error(error)[1] if error is not None else None
    return {
        "configuration": _configuration_read_model(outcome.configuration),
        "connection": outcome.snapshot.connection.value,
        "operationalState": outcome.snapshot.operational_state.value,
        "observedAt": _datetime(outcome.snapshot.observed_at),
        "reachable": error is None,
        "connectionError": (
            None
            if error is None
            else {
                "code": error.code.value,
                "message": public_message,
                "retryable": error.retryable,
                "vendorCode": error.vendor_code,
            }
        ),
    }


def _public_connection_error(error: PrinterAdapterError) -> tuple[str, str]:
    if error.code == PrinterErrorCode.CONNECTION_UNAVAILABLE:
        return (
            "printer_connection_unavailable",
            "FoxForge could not reach the printer on the configured LAN address.",
        )
    if error.code == PrinterErrorCode.AUTHENTICATION_FAILED:
        return (
            "printer_connection_authentication_failed",
            "The printer rejected the configured LAN credentials.",
        )
    if error.code == PrinterErrorCode.TIMEOUT and error.vendor_code == "initial_state_timeout":
        return (
            "printer_initial_state_timeout",
            "MQTT connected, but FoxForge did not receive initial state. Verify the Bambu serial number and LAN mode.",
        )
    if error.code == PrinterErrorCode.TIMEOUT:
        return (
            "printer_connection_timeout",
            "The printer connection timed out before FoxForge received a valid initial state.",
        )
    if error.code == PrinterErrorCode.INTERNAL_ADAPTER_ERROR:
        return (
            "printer_connection_internal_adapter_error",
            "The printer adapter failed while establishing the connection.",
        )
    return (
        f"printer_connection_{error.code.value}",
        "Printer connection validation failed.",
    )


def _public_connection_message(code: str) -> str | None:
    messages = {
        "printer_connection_unavailable": "FoxForge could not reach the printer on the configured LAN address.",
        "printer_connection_authentication_failed": "The printer rejected the configured LAN credentials.",
        "printer_initial_state_timeout": (
            "MQTT connected, but FoxForge did not receive initial state. Verify the Bambu serial number and LAN mode."
        ),
        "printer_connection_timeout": (
            "The printer connection timed out before FoxForge received a valid initial state."
        ),
        "printer_connection_internal_adapter_error": ("The printer adapter failed while establishing the connection."),
    }
    return messages.get(code)


def _required_text(mapping: dict[str, object], field_name: str) -> str:
    value = mapping.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional text fields must be strings or null")
    cleaned = value.strip()
    return cleaned or None


def _moonraker_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Moonraker baseUrl must be an absolute http:// or https:// URL")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ValueError("Moonraker baseUrl must not contain credentials, query or fragment")
    return value.rstrip("/")


def _datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


@web.middleware
async def _request_context(request: web.Request, handler: _JSON_HANDLER) -> web.StreamResponse:
    candidate = request.headers.get("X-Request-Id")
    request[_REQUEST_ID_KEY] = (
        candidate if candidate is not None and _REQUEST_ID_RE.fullmatch(candidate) else str(uuid4())
    )
    return await handler(request)


@web.middleware
async def _response_headers(request: web.Request, handler: _JSON_HANDLER) -> web.StreamResponse:
    response = await handler(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-FoxForge-Api-Version"] = API_VERSION
    response.headers["X-Request-Id"] = request[_REQUEST_ID_KEY]
    return response


def _add_get(app: web.Application, path: str, handler: _JSON_HANDLER) -> None:
    app.router.add_get(path, handler)
