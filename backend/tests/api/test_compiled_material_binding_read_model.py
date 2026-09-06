# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from foxforge.api.v1.read_models import _queue_entry
from foxforge.application.fleet import FleetService
from foxforge.application.queue import InMemoryQueueStore, QueueService
from foxforge.domain.printers.capabilities import MaterialBinding
from tests.helpers import make_artifact


def test_queue_read_model_exposes_compiled_toolhead_identity(tmp_path, printer_identity) -> None:
    queue = QueueService(FleetService([]), InMemoryQueueStore())
    entry = queue.enqueue(
        printer_identity.printer_id,
        make_artifact(tmp_path / "job.gcode"),
        material_bindings=(
            MaterialBinding(
                material_index=0,
                slot_id="bambu:unit:255:tray:0",
                toolhead_id="bambu:toolhead:0",
            ),
        ),
    )

    model = _queue_entry(entry)

    assert model["request"]["materialBindings"] == [
        {
            "materialIndex": 0,
            "slotId": "bambu:unit:255:tray:0",
            "toolheadId": "bambu:toolhead:0",
        }
    ]
