# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from foxforge.application.fleet import FleetService
from foxforge.application.inventory import InventoryService
from foxforge.application.queue import QueueEntry, QueueService
from foxforge.domain.inventory import Spool
from foxforge.domain.printers import ActiveJobSnapshot, PrinterSnapshot
from foxforge.domain.printers.capabilities import (
    JobControlCapability,
    MaterialSystemCapability,
    MaterialSystemSnapshot,
    PrintExecutionCapability,
)

API_VERSION = "1"


def fleet_read_model(fleet: FleetService) -> dict[str, Any]:
    identities = {identity.printer_id: identity for identity in fleet.identities()}
    printers: list[dict[str, Any]] = []

    for printer_id in fleet.printer_ids:
        identity = identities[printer_id]
        snapshot = fleet.snapshot(printer_id)
        print_execution = fleet.capability(printer_id, PrintExecutionCapability)
        material_system = fleet.capability(printer_id, MaterialSystemCapability)
        job_control = fleet.capability(printer_id, JobControlCapability)

        capabilities: list[dict[str, Any]] = []
        for capability in (print_execution, material_system):
            if capability is None:
                continue
            descriptor = capability.descriptor
            capabilities.append(
                {
                    "capabilityId": descriptor.capability_id,
                    "majorVersion": descriptor.major_version,
                }
            )
        if job_control is not None:
            descriptor = job_control.descriptor
            capabilities.append(
                {
                    "capabilityId": descriptor.capability_id,
                    "majorVersion": descriptor.major_version,
                    "supportedActions": sorted(action.value for action in descriptor.supported_actions),
                    "requiresVendorJobIdentity": descriptor.requires_vendor_job_identity,
                }
            )

        printer: dict[str, Any] = {
            "identity": {
                "printerId": identity.printer_id,
                "displayName": identity.display_name,
                "vendor": identity.vendor,
                "model": identity.model,
                "serialNumber": identity.serial_number,
                "adapterKind": identity.adapter_kind,
            },
            "snapshot": _printer_snapshot(snapshot),
            "capabilities": capabilities,
        }
        if material_system is not None:
            printer["materialSystem"] = _material_system_snapshot(material_system.snapshot())
        printers.append(printer)

    return {"apiVersion": API_VERSION, "printers": printers}


def queue_read_model(queue: QueueService) -> dict[str, Any]:
    return {
        "apiVersion": API_VERSION,
        "entries": [_queue_entry(entry) for entry in queue.list()],
    }


def inventory_read_model(inventory: InventoryService) -> dict[str, Any]:
    return {
        "apiVersion": API_VERSION,
        "spools": [_spool(inventory, spool) for spool in inventory.list_spools(include_archived=True)],
    }


def _printer_snapshot(snapshot: PrinterSnapshot) -> dict[str, Any]:
    return {
        "printerId": snapshot.printer_id,
        "connection": snapshot.connection.value,
        "operationalState": snapshot.operational_state.value,
        "activeJob": None if snapshot.active_job is None else _active_job(snapshot.active_job),
        "observedAt": _datetime(snapshot.observed_at),
        "stale": snapshot.stale,
        "faultSummary": [
            {
                "code": fault.code,
                "severity": fault.severity.value,
                "message": fault.message,
            }
            for fault in snapshot.fault_summary
        ],
    }


def _active_job(job: ActiveJobSnapshot) -> dict[str, Any]:
    return {
        "vendorJobId": job.vendor_job_id,
        "name": job.name,
        "state": job.state.value,
        "progress": job.progress,
        "elapsedSeconds": job.elapsed_seconds,
        "remainingSeconds": job.remaining_seconds,
        "currentLayer": job.current_layer,
        "totalLayers": job.total_layers,
    }


def _material_system_snapshot(snapshot: MaterialSystemSnapshot) -> dict[str, Any]:
    return {
        "printerId": snapshot.printer_id,
        "units": [
            {
                "unitId": unit.unit_id,
                "kind": unit.kind.value,
                "label": unit.label,
                "position": unit.position,
                "slots": [
                    {
                        "slotId": slot.slot_id,
                        "unitId": slot.unit_id,
                        "position": slot.position,
                        "label": slot.label,
                        "presence": slot.presence.value,
                        "activity": slot.activity.value,
                        "detectedMaterial": (
                            None
                            if slot.detected_material is None
                            else {
                                "materialFamily": slot.detected_material.material_family,
                                "vendorName": slot.detected_material.vendor_name,
                                "productName": slot.detected_material.product_name,
                                "rgbaHex": (
                                    None
                                    if slot.detected_material.color is None
                                    else slot.detected_material.color.rgba_hex
                                ),
                                "tag": (
                                    None
                                    if slot.detected_material.tag is None
                                    else {
                                        "scheme": slot.detected_material.tag.scheme,
                                        "value": slot.detected_material.tag.value,
                                    }
                                ),
                                "remainingFraction": slot.detected_material.remaining_fraction,
                            }
                        ),
                    }
                    for slot in unit.slots
                ],
            }
            for unit in snapshot.units
        ],
        "observedAt": _datetime(snapshot.observed_at),
        "stale": snapshot.stale,
    }


def _queue_entry(entry: QueueEntry) -> dict[str, Any]:
    assessment = entry.assessment
    receipt = entry.receipt
    error = entry.error
    request = entry.request
    return {
        "queueId": str(entry.queue_id),
        "printerId": entry.printer_id,
        "state": entry.state.value,
        "createdAt": _datetime(entry.created_at),
        "updatedAt": _datetime(entry.updated_at),
        "attemptCount": entry.attempt_count,
        "lastAttemptAt": None if entry.last_attempt_at is None else _datetime(entry.last_attempt_at),
        "request": {
            "dispatchId": str(request.dispatch_id),
            "requestedName": request.requested_name,
            "artifact": {
                "artifactId": request.artifact.artifact_id,
                "filename": request.artifact.filename,
                "format": request.artifact.format.value,
                "sizeBytes": request.artifact.size_bytes,
                "sha256": request.artifact.sha256,
            },
            "selection": (None if request.selection is None else {"plateIndex": request.selection.plate_index}),
            "materialBindings": [
                {"materialIndex": binding.material_index, "slotId": binding.slot_id}
                for binding in request.material_bindings
            ],
        },
        "assessment": (
            None
            if assessment is None
            else {
                "eligible": assessment.eligible,
                "observedAt": _datetime(assessment.observed_at),
                "blockers": [
                    {"code": blocker.code.value, "message": blocker.message} for blocker in assessment.blockers
                ],
            }
        ),
        "receipt": (
            None
            if receipt is None
            else {
                "dispatchId": str(receipt.dispatch_id),
                "acceptedAt": _datetime(receipt.accepted_at),
                "vendorJobId": receipt.vendor_job_id,
                "artifactSha256": receipt.artifact_sha256,
            }
        ),
        "error": (
            None
            if error is None
            else {
                "code": error.code.value,
                "message": error.message,
                "retryable": error.retryable,
                "vendorCode": error.vendor_code,
            }
        ),
    }


def _spool(inventory: InventoryService, spool: Spool) -> dict[str, Any]:
    balance = inventory.balance(spool.spool_id)
    assignment = inventory.assignment_for_spool(spool.spool_id)
    return {
        "spoolId": str(spool.spool_id),
        "materialFamily": spool.material_family,
        "manufacturer": spool.manufacturer,
        "productName": spool.product_name,
        "rgbaHex": None if spool.color is None else spool.color.rgba_hex,
        "initialFilamentMassG": str(balance.initial_filament_mass_g),
        "remainingFilamentMassG": str(balance.remaining_filament_mass_g),
        "usedFilamentMassG": str(balance.used_filament_mass_g),
        "usedFraction": str(balance.used_fraction),
        "emptySpoolMassG": None if spool.empty_spool_mass_g is None else str(spool.empty_spool_mass_g),
        "purchaseDate": None if spool.purchase_date is None else spool.purchase_date.isoformat(),
        "createdAt": _datetime(spool.created_at),
        "updatedAt": _datetime(spool.updated_at),
        "archived": spool.archived,
        "assignment": (
            None
            if assignment is None
            else {
                "printerId": assignment.printer_id,
                "slotId": assignment.slot_id,
                "assignedAt": _datetime(assignment.assigned_at),
            }
        ),
    }


def _datetime(value: datetime) -> str:
    normalized = value.astimezone(UTC)
    return normalized.isoformat().replace("+00:00", "Z")
