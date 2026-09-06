# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from foxforge.application.fleet import FleetService
from foxforge.application.queue import QueueService
from foxforge.domain.printers.capabilities import MaterialBinding
from foxforge.infrastructure.queue import SQLiteQueueStore
from tests.helpers import make_artifact


def test_sqlite_queue_round_trip_preserves_compiled_toolhead_identity(tmp_path, printer_identity) -> None:
    database = tmp_path / "queue.db"
    queue = QueueService(FleetService([]), SQLiteQueueStore(database))
    artifact = make_artifact(tmp_path / "job.gcode")
    entry = queue.enqueue(
        printer_identity.printer_id,
        artifact,
        material_bindings=(
            MaterialBinding(
                material_index=0,
                slot_id="bambu:unit:255:tray:0",
                toolhead_id="bambu:toolhead:0",
            ),
        ),
    )

    restored = SQLiteQueueStore(database).get(entry.queue_id)

    assert restored is not None
    assert restored.request.material_bindings == entry.request.material_bindings
    assert restored.request.material_bindings[0].toolhead_id == "bambu:toolhead:0"
