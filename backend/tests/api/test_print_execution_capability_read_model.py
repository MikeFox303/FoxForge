# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from foxforge.api.v1.read_models import fleet_read_model
from foxforge.application.fleet import FleetService
from foxforge.domain.printers.capabilities import PrintArtifactFormat
from foxforge.testing import build_fake_printer


def test_fleet_read_model_exposes_print_execution_descriptor_without_vendor_fields(printer_identity) -> None:
    adapter, _, _ = build_fake_printer(
        printer_identity,
        accepted_formats=frozenset({PrintArtifactFormat.THREE_MF}),
        supports_plate_selection=True,
        supports_material_bindings=True,
    )
    fleet = FleetService([adapter])

    printer = fleet_read_model(fleet)["printers"][0]
    capability = next(item for item in printer["capabilities"] if item["capabilityId"] == "foxforge.print_execution")

    assert capability == {
        "capabilityId": "foxforge.print_execution",
        "majorVersion": 1,
        "acceptedFormats": ["3mf"],
        "supportsPlateSelection": True,
        "supportsMaterialBindings": True,
    }
    assert "vendor" not in capability
    assert "model" not in capability
