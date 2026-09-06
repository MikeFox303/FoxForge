# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from urllib.parse import unquote

from aiohttp import web

from foxforge.application.artifacts import (
    ArtifactChangedDuringInspectionError,
    ArtifactNotFoundError,
    ArtifactPrintPlan,
    ArtifactStore,
    InvalidThreeMfError,
    UnsupportedPrintPlanArtifactError,
    inspect_print_plan,
)

from .http import add_authenticated_route, command_error
from .security import CommandPermission


def register_artifact_read_routes(app: web.Application, *, artifacts: ArtifactStore) -> None:
    """Register authenticated reads of immutable staged-artifact metadata."""

    async def print_plan(request: web.Request) -> web.Response:
        try:
            artifact_id = _artifact_id(request.match_info.get("artifact_id"))
            artifact = artifacts.get(artifact_id)
            plan = inspect_print_plan(artifact)
        except ArtifactNotFoundError:
            return command_error(request, status=404, code="artifact_not_found", message="Artifact was not found.")
        except ArtifactChangedDuringInspectionError as error:
            return command_error(request, status=409, code="artifact_changed", message=str(error))
        except UnsupportedPrintPlanArtifactError as error:
            return command_error(request, status=422, code="unsupported_artifact", message=str(error))
        except InvalidThreeMfError as error:
            return command_error(request, status=422, code="invalid_3mf", message=str(error))
        except (ValueError, TypeError) as error:
            return command_error(request, status=400, code="invalid_request", message=str(error))

        return web.json_response(_print_plan_read_model(plan))

    add_authenticated_route(
        app,
        "GET",
        "/api/v1/artifacts/{artifact_id}/print-plan",
        CommandPermission.QUEUE_WRITE,
        print_plan,
    )


def _artifact_id(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("artifactId must be a SHA-256 hexadecimal digest")
    text = unquote(value).strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError("artifactId must be a SHA-256 hexadecimal digest")
    return text


def _print_plan_read_model(plan: ArtifactPrintPlan) -> dict[str, object]:
    return {
        "artifactId": plan.artifact_id,
        "artifactSha256": plan.artifact_sha256,
        "readyForRouting": plan.ready_for_routing,
        "plates": [
            {
                "plateIndex": plate.plate_index,
                "readyForRouting": plate.ready_for_routing,
                "materialRequirements": [
                    {
                        "materialIndex": requirement.material_index,
                        "materialFamily": requirement.material_family,
                        "rgbaHex": requirement.color_rgba_hex,
                        "profileName": requirement.profile_name,
                        "expectedToolheadPosition": requirement.expected_toolhead_position,
                    }
                    for requirement in plate.material_requirements
                ],
            }
            for plate in plan.plates
        ],
        "issues": [
            {
                "code": issue.code.value,
                "severity": issue.severity.value,
                "message": issue.message,
                "plateIndex": issue.plate_index,
            }
            for issue in plan.issues
        ],
    }
