# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from uuid import uuid4

from foxforge.api.v1.queue_commands import _same_client_enqueue_intent
from foxforge.domain.printers.capabilities import MaterialBinding, PrintExecutionRequest
from tests.helpers import make_artifact


def test_enqueue_client_intent_ignores_compiler_owned_toolhead(tmp_path) -> None:
    artifact = make_artifact(tmp_path / "job.gcode")
    dispatch_id = uuid4()
    expected = PrintExecutionRequest(
        dispatch_id=dispatch_id,
        artifact=artifact,
        material_bindings=(MaterialBinding(0, "slot-a"),),
    )
    compiled = PrintExecutionRequest(
        dispatch_id=dispatch_id,
        artifact=artifact,
        material_bindings=(MaterialBinding(0, "slot-a", "toolhead-0"),),
    )

    assert _same_client_enqueue_intent(compiled, expected)


def test_enqueue_client_intent_still_rejects_changed_source_slot(tmp_path) -> None:
    artifact = make_artifact(tmp_path / "job.gcode")
    dispatch_id = uuid4()
    expected = PrintExecutionRequest(
        dispatch_id=dispatch_id,
        artifact=artifact,
        material_bindings=(MaterialBinding(0, "slot-a"),),
    )
    changed = PrintExecutionRequest(
        dispatch_id=dispatch_id,
        artifact=artifact,
        material_bindings=(MaterialBinding(0, "slot-b", "toolhead-0"),),
    )

    assert not _same_client_enqueue_intent(changed, expected)
