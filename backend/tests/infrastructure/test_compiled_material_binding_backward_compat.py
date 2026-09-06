# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from foxforge.infrastructure.queue.sqlite_store import _decode_request
from tests.helpers import make_artifact


def test_legacy_queue_binding_without_toolhead_decodes_as_uncompiled(tmp_path) -> None:
    artifact = make_artifact(tmp_path / "legacy.gcode")
    request = _decode_request(
        {
            "dispatch_id": "00000000-0000-0000-0000-000000000001",
            "artifact": {
                "artifact_id": artifact.artifact_id,
                "path": str(artifact.path),
                "filename": artifact.filename,
                "format": artifact.format.value,
                "size_bytes": artifact.size_bytes,
                "sha256": artifact.sha256,
            },
            "selection": None,
            "material_bindings": [
                {
                    "material_index": 0,
                    "slot_id": "bambu:unit:0:tray:0",
                }
            ],
            "requested_name": None,
        }
    )

    assert request.material_bindings[0].toolhead_id is None
