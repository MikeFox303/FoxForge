# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

import asyncio
from uuid import UUID, uuid4

from aiohttp.test_utils import TestClient, TestServer

from foxforge.api.v1 import BearerCommandSecurity, create_api_v1_app
from foxforge.api.v1.command_audit import install_command_audit
from foxforge.api.v1.job_control_commands import register_job_control_command_routes
from foxforge.application.commands import (
    CommandAuditOutcome,
    InMemoryCommandAuditStore,
    InMemoryCommandIdempotencyStore,
)
from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InMemoryInventoryStore, InventoryService
from foxforge.application.queue import InMemoryQueueStore, QueueService
from foxforge.domain.printers import (
    ActiveJobSnapshot,
    ConnectionState,
    JobState,
    OperationalState,
    PrinterAdapterError,
    PrinterErrorCode,
    PrinterIdentity,
    PrinterSnapshot,
    utc_now,
)
from foxforge.domain.printers.capabilities import (
    JOB_CONTROL_CAPABILITY_ID,
    JOB_CONTROL_MAJOR_VERSION,
    JobControlAction,
    JobControlAssessment,
    JobControlCapability,
    JobControlDescriptor,
    JobControlReceipt,
    JobControlRequest,
)
from foxforge.testing import FakePrinterAdapter

_TOKEN = "test-job-control-token-0123456789abcdef"


class _ControlCapability:
    def __init__(self, adapter: FakePrinterAdapter) -> None:
        self._adapter = adapter
        self.execute_count = 0
        self.indeterminate = False
        self._descriptor = JobControlDescriptor(
            capability_id=JOB_CONTROL_CAPABILITY_ID,
            major_version=JOB_CONTROL_MAJOR_VERSION,
            supported_actions=frozenset(JobControlAction),
        )

    @property
    def descriptor(self) -> JobControlDescriptor:
        return self._descriptor

    async def assess(self, request: JobControlRequest) -> JobControlAssessment:
        return JobControlAssessment(eligible=True, blockers=(), observed_at=self._adapter.snapshot().observed_at)

    async def execute(self, request: JobControlRequest) -> JobControlReceipt:
        self.execute_count += 1
        if self.indeterminate:
            raise PrinterAdapterError(
                PrinterErrorCode.INDETERMINATE,
                "control outcome unknown",
                retryable=False,
            )
        return JobControlReceipt(
            control_id=request.control_id,
            action=request.action,
            accepted_at=self._adapter.snapshot().observed_at,
            vendor_job_id=request.expected_vendor_job_id,
        )


def _app() -> tuple[TestClient, _ControlCapability, InMemoryCommandAuditStore]:
    identity = PrinterIdentity(
        printer_id="printer-1",
        display_name="Printer 1",
        vendor="Test",
        model=None,
        serial_number=None,
        adapter_kind="fake",
    )
    adapter = FakePrinterAdapter(identity)
    adapter.set_snapshot(
        PrinterSnapshot(
            printer_id="printer-1",
            connection=ConnectionState.CONNECTED,
            operational_state=OperationalState.PRINTING,
            active_job=ActiveJobSnapshot(
                vendor_job_id="vendor-job-1",
                name="job.gcode",
                state=JobState.PRINTING,
                progress=0.5,
                elapsed_seconds=30,
                remaining_seconds=30,
                current_layer=2,
                total_layers=4,
            ),
            observed_at=utc_now(),
            stale=False,
        )
    )
    capability = _ControlCapability(adapter)
    adapter.register_capability(JobControlCapability, capability)
    fleet = FleetService([adapter])
    idempotency = InMemoryCommandIdempotencyStore()
    audit = InMemoryCommandAuditStore()
    security = BearerCommandSecurity(_TOKEN)
    app = create_api_v1_app(
        fleet=fleet,
        queue=QueueService(fleet, InMemoryQueueStore()),
        inventory=InventoryService(InMemoryInventoryStore()),
        command_security=security,
        command_idempotency=idempotency,
    )
    register_job_control_command_routes(app, fleet=fleet)
    install_command_audit(app, security=security, store=audit)
    return TestClient(TestServer(app)), capability, audit


def _payload(control_id: UUID | None = None, *, action: str = "pause") -> dict[str, str]:
    return {
        "controlId": str(control_id or uuid4()),
        "action": action,
        "expectedVendorJobId": "vendor-job-1",
    }


def _headers(key: str, request_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {_TOKEN}", "Idempotency-Key": key}
    if request_id is not None:
        headers["X-Request-Id"] = request_id
    return headers


def test_job_control_success_and_completed_replay_execute_once() -> None:
    async def scenario() -> None:
        client, capability, _ = _app()
        await client.start_server()
        try:
            payload = _payload()
            first = await client.post(
                "/api/v1/printers/printer-1/job-control",
                json=payload,
                headers=_headers("key-1"),
            )
            assert first.status == 200
            assert (await first.json())["replayed"] is False

            replay = await client.post(
                "/api/v1/printers/printer-1/job-control",
                json=payload,
                headers=_headers("key-1"),
            )
            assert replay.status == 200
            assert (await replay.json())["replayed"] is True
            assert capability.execute_count == 1
        finally:
            await client.close()

    asyncio.run(scenario())


def test_job_control_same_key_rejects_changed_request() -> None:
    async def scenario() -> None:
        client, capability, _ = _app()
        await client.start_server()
        try:
            control_id = uuid4()
            first = await client.post(
                "/api/v1/printers/printer-1/job-control",
                json=_payload(control_id),
                headers=_headers("key-2"),
            )
            assert first.status == 200

            changed = await client.post(
                "/api/v1/printers/printer-1/job-control",
                json=_payload(control_id, action="cancel"),
                headers=_headers("key-2"),
            )
            assert changed.status == 409
            assert (await changed.json())["error"]["code"] == "idempotency_conflict"
            assert capability.execute_count == 1
        finally:
            await client.close()

    asyncio.run(scenario())


def test_indeterminate_command_stays_unresolved_and_is_not_reexecuted() -> None:
    async def scenario() -> None:
        client, capability, _ = _app()
        capability.indeterminate = True
        await client.start_server()
        try:
            payload = _payload()
            first = await client.post(
                "/api/v1/printers/printer-1/job-control",
                json=payload,
                headers=_headers("key-3"),
            )
            assert first.status == 409
            assert (await first.json())["error"]["code"] == "job_control_indeterminate"

            replay = await client.post(
                "/api/v1/printers/printer-1/job-control",
                json=payload,
                headers=_headers("key-3"),
            )
            assert replay.status == 409
            assert (await replay.json())["error"]["code"] == "job_control_reconciliation_required"
            assert capability.execute_count == 1
        finally:
            await client.close()

    asyncio.run(scenario())


def test_job_control_is_recorded_in_command_audit() -> None:
    async def scenario() -> None:
        client, capability, audit = _app()
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/printers/printer-1/job-control",
                json=_payload(),
                headers=_headers("key-audit", "req-job-control-audit"),
            )
            assert response.status == 200
            assert capability.execute_count == 1

            records = audit.list_for_request("req-job-control-audit")
            assert [record.action for record in records] == ["printer.job_control", "printer.job_control"]
            assert [record.target_ref for record in records] == ["printer-1", "printer-1"]
            assert [record.outcome for record in records] == [
                CommandAuditOutcome.ACCEPTED,
                CommandAuditOutcome.COMPLETED,
            ]
        finally:
            await client.close()

    asyncio.run(scenario())


def test_job_control_requires_authentication() -> None:
    async def scenario() -> None:
        client, capability, _ = _app()
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/printers/printer-1/job-control",
                json=_payload(),
                headers={"Idempotency-Key": "key-4"},
            )
            assert response.status == 401
            assert capability.execute_count == 0
        finally:
            await client.close()

    asyncio.run(scenario())
