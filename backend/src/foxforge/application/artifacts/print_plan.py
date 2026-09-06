# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Immutable staged-artifact inspection for sliced 3MF print plans.

This is newly written FoxForge code. The parsing strategy is informed by
Bambuddy's 3MF handling, but intentionally keeps the first routing gate small:
material indices come from the embedded plate G-code that would actually be
sent to the printer, while project_settings.config is metadata-only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from dataclasses import dataclass
from enum import StrEnum
from typing import BinaryIO

from foxforge.domain.printers.capabilities import LocalPrintArtifact, PrintArtifactFormat

from ._bambu_3mf_toolheads import parse_bambu_toolhead_expectations

_MAX_ZIP_MEMBERS = 4096
_MAX_ZIP_MEMBER_NAME = 1024
_MAX_PROJECT_SETTINGS_BYTES = 4 * 1024 * 1024
_MAX_PLATE_GCODE_BYTES = 1024 * 1024 * 1024
_MAX_GCODE_LINE_BYTES = 4096
_MAX_MATERIAL_INDEX = 255
_READ_CHUNK_BYTES = 1024 * 1024
_GCODE_CHUNK_BYTES = 64 * 1024

_PLATE_GCODE_RE = re.compile(r"^Metadata/plate_(\d+)\.gcode$", re.IGNORECASE)
_M620_RE = re.compile(rb"^\s*M620\s+S(\d+)", re.IGNORECASE)


class PrintPlanIssueSeverity(StrEnum):
    WARNING = "warning"
    BLOCKING = "blocking"


class PrintPlanIssueCode(StrEnum):
    NO_SLICED_PLATES = "no_sliced_plates"
    MATERIAL_REQUIREMENTS_UNKNOWN = "material_requirements_unknown"
    MATERIAL_INDEX_OUT_OF_RANGE = "material_index_out_of_range"
    PROJECT_METADATA_INVALID = "project_metadata_invalid"
    TOOLHEAD_METADATA_INVALID = "toolhead_metadata_invalid"


@dataclass(frozen=True, slots=True)
class PrintPlanIssue:
    code: PrintPlanIssueCode
    severity: PrintPlanIssueSeverity
    message: str
    plate_index: int | None = None

    def __post_init__(self) -> None:
        if not self.message:
            raise ValueError("print-plan issue message must not be empty")
        if self.plate_index is not None and self.plate_index < 0:
            raise ValueError("plate_index must be zero-based and non-negative")


@dataclass(frozen=True, slots=True)
class PrintPlanMaterialRequirement:
    material_index: int
    material_family: str | None
    color_rgba_hex: str | None
    profile_name: str | None
    expected_toolhead_position: int | None = None

    def __post_init__(self) -> None:
        if self.material_index < 0:
            raise ValueError("material_index must be zero-based and non-negative")
        if self.expected_toolhead_position is not None and self.expected_toolhead_position < 0:
            raise ValueError("expected_toolhead_position must be non-negative when present")


@dataclass(frozen=True, slots=True)
class PrintPlanPlate:
    plate_index: int
    material_requirements: tuple[PrintPlanMaterialRequirement, ...]
    ready_for_routing: bool

    def __post_init__(self) -> None:
        if self.plate_index < 0:
            raise ValueError("plate_index must be zero-based and non-negative")
        indices = [item.material_index for item in self.material_requirements]
        if indices != sorted(indices) or len(indices) != len(set(indices)):
            raise ValueError("plate material requirements must have unique sorted indices")
        if self.ready_for_routing and not self.material_requirements:
            raise ValueError("a routing-ready plate must have at least one material requirement")


@dataclass(frozen=True, slots=True)
class ArtifactPrintPlan:
    artifact_id: str
    artifact_sha256: str
    plates: tuple[PrintPlanPlate, ...]
    issues: tuple[PrintPlanIssue, ...]

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("artifact_id must not be empty")
        if len(self.artifact_sha256) != 64:
            raise ValueError("artifact_sha256 must be a SHA-256 digest")
        plate_indices = [plate.plate_index for plate in self.plates]
        if plate_indices != sorted(plate_indices) or len(plate_indices) != len(set(plate_indices)):
            raise ValueError("print-plan plate indices must be unique and sorted")

    @property
    def ready_for_routing(self) -> bool:
        return (
            bool(self.plates)
            and all(plate.ready_for_routing for plate in self.plates)
            and not any(
                issue.severity == PrintPlanIssueSeverity.BLOCKING and issue.plate_index is None for issue in self.issues
            )
        )


class PrintPlanInspectionError(RuntimeError):
    pass


class UnsupportedPrintPlanArtifactError(PrintPlanInspectionError):
    pass


class ArtifactChangedDuringInspectionError(PrintPlanInspectionError):
    pass


class InvalidThreeMfError(PrintPlanInspectionError):
    pass


@dataclass(frozen=True, slots=True)
class _ProjectMaterialMetadata:
    material_family: str | None
    color_rgba_hex: str | None
    profile_name: str | None


def inspect_print_plan(artifact: LocalPrintArtifact) -> ArtifactPrintPlan:
    """Inspect one content-addressed staged 3MF without extracting it to disk.

    The same open file descriptor is hash-checked before and after ZIP parsing.
    This makes the returned plan evidence for one immutable artifact version,
    rather than a best-effort read of a mutable filesystem path.
    """

    if artifact.format != PrintArtifactFormat.THREE_MF:
        raise UnsupportedPrintPlanArtifactError("Print-plan inspection currently requires a staged 3MF artifact")

    try:
        with artifact.path.open("rb") as handle:
            _verify_open_artifact(handle, artifact)
            handle.seek(0)
            plan = _inspect_verified_three_mf(handle, artifact)
            handle.seek(0)
            _verify_open_artifact(handle, artifact)
            return plan
    except FileNotFoundError as error:
        raise ArtifactChangedDuringInspectionError("Staged artifact is no longer available") from error
    except PermissionError as error:
        raise ArtifactChangedDuringInspectionError("Staged artifact is no longer readable") from error
    except OSError as error:
        raise ArtifactChangedDuringInspectionError("Staged artifact could not be read safely") from error


def _inspect_verified_three_mf(handle: BinaryIO, artifact: LocalPrintArtifact) -> ArtifactPrintPlan:
    try:
        with zipfile.ZipFile(handle, "r") as archive:
            infos = archive.infolist()
            _validate_archive_shape(infos)
            plate_infos = _plate_gcode_members(infos)
            metadata, metadata_issue = _project_material_metadata(archive, infos)

            issues: list[PrintPlanIssue] = []
            if metadata_issue is not None:
                issues.append(metadata_issue)

            if not plate_infos:
                issues.append(
                    PrintPlanIssue(
                        code=PrintPlanIssueCode.NO_SLICED_PLATES,
                        severity=PrintPlanIssueSeverity.BLOCKING,
                        message="3MF does not contain Bambu-style Metadata/plate_N.gcode members",
                    )
                )
                return ArtifactPrintPlan(
                    artifact_id=artifact.artifact_id,
                    artifact_sha256=artifact.sha256,
                    plates=(),
                    issues=tuple(issues),
                )

            toolhead_expectations, toolhead_warnings = parse_bambu_toolhead_expectations(
                archive,
                infos,
                plate_indices=tuple(plate_number - 1 for plate_number in sorted(plate_infos)),
            )
            issues.extend(
                PrintPlanIssue(
                    code=PrintPlanIssueCode.TOOLHEAD_METADATA_INVALID,
                    severity=PrintPlanIssueSeverity.WARNING,
                    message=warning.message,
                    plate_index=warning.plate_index,
                )
                for warning in toolhead_warnings
            )

            plates: list[PrintPlanPlate] = []
            for plate_number, info in sorted(plate_infos.items()):
                plate_index = plate_number - 1
                material_indices, plate_issues = _scan_plate_material_indices(archive, info, plate_index=plate_index)
                issues.extend(plate_issues)
                requirements = tuple(
                    PrintPlanMaterialRequirement(
                        material_index=material_index,
                        material_family=metadata.get(material_index, _EMPTY_METADATA).material_family,
                        color_rgba_hex=metadata.get(material_index, _EMPTY_METADATA).color_rgba_hex,
                        profile_name=metadata.get(material_index, _EMPTY_METADATA).profile_name,
                        expected_toolhead_position=toolhead_expectations.get(plate_index, {}).get(material_index),
                    )
                    for material_index in sorted(material_indices)
                )
                has_blocker = any(issue.severity == PrintPlanIssueSeverity.BLOCKING for issue in plate_issues)
                plates.append(
                    PrintPlanPlate(
                        plate_index=plate_index,
                        material_requirements=requirements,
                        ready_for_routing=bool(requirements) and not has_blocker,
                    )
                )

            return ArtifactPrintPlan(
                artifact_id=artifact.artifact_id,
                artifact_sha256=artifact.sha256,
                plates=tuple(plates),
                issues=tuple(issues),
            )
    except InvalidThreeMfError:
        raise
    except zipfile.BadZipFile as error:
        raise InvalidThreeMfError("Artifact is not a valid ZIP-based 3MF file") from error
    except (RuntimeError, NotImplementedError) as error:
        raise InvalidThreeMfError("3MF uses an unsupported or encrypted ZIP member") from error


_EMPTY_METADATA = _ProjectMaterialMetadata(None, None, None)


def _verify_open_artifact(handle: BinaryIO, artifact: LocalPrintArtifact) -> None:
    stat = os.fstat(handle.fileno())
    if stat.st_size != artifact.size_bytes:
        raise ArtifactChangedDuringInspectionError("Staged artifact size no longer matches its immutable metadata")

    digest = hashlib.sha256()
    while chunk := handle.read(_READ_CHUNK_BYTES):
        digest.update(chunk)
    if digest.hexdigest() != artifact.sha256:
        raise ArtifactChangedDuringInspectionError("Staged artifact SHA-256 no longer matches its immutable metadata")


def _validate_archive_shape(infos: list[zipfile.ZipInfo]) -> None:
    if len(infos) > _MAX_ZIP_MEMBERS:
        raise InvalidThreeMfError(f"3MF contains more than {_MAX_ZIP_MEMBERS} ZIP members")
    if any(len(info.filename) > _MAX_ZIP_MEMBER_NAME for info in infos):
        raise InvalidThreeMfError("3MF contains an excessively long ZIP member name")


def _plate_gcode_members(infos: list[zipfile.ZipInfo]) -> dict[int, zipfile.ZipInfo]:
    result: dict[int, zipfile.ZipInfo] = {}
    for info in infos:
        match = _PLATE_GCODE_RE.fullmatch(info.filename)
        if match is None:
            continue
        plate_number = int(match.group(1))
        if plate_number <= 0:
            raise InvalidThreeMfError("3MF plate numbers must be one-based positive integers")
        if plate_number in result:
            raise InvalidThreeMfError(f"3MF contains more than one G-code member for plate {plate_number}")
        if info.flag_bits & 0x1:
            raise InvalidThreeMfError("Encrypted plate G-code members are not supported")
        if info.file_size > _MAX_PLATE_GCODE_BYTES:
            raise InvalidThreeMfError(
                f"Plate {plate_number} G-code exceeds the {_MAX_PLATE_GCODE_BYTES}-byte inspection limit"
            )
        result[plate_number] = info
    return result


def _scan_plate_material_indices(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    plate_index: int,
) -> tuple[set[int], list[PrintPlanIssue]]:
    material_indices: set[int] = set()
    issues: list[PrintPlanIssue] = []
    pending = b""

    with archive.open(info, "r") as member:
        while chunk := member.read(_GCODE_CHUNK_BYTES):
            pending += chunk
            while True:
                newline = pending.find(b"\n")
                if newline < 0:
                    break
                line = pending[:newline]
                pending = pending[newline + 1 :]
                _scan_gcode_line(line, material_indices, issues, plate_index=plate_index)
            if len(pending) > _MAX_GCODE_LINE_BYTES:
                raise InvalidThreeMfError("3MF plate G-code contains an excessively long line")

    if pending:
        _scan_gcode_line(pending, material_indices, issues, plate_index=plate_index)

    if not material_indices:
        issues.append(
            PrintPlanIssue(
                code=PrintPlanIssueCode.MATERIAL_REQUIREMENTS_UNKNOWN,
                severity=PrintPlanIssueSeverity.BLOCKING,
                message="Plate G-code does not expose any numeric M620 material selection",
                plate_index=plate_index,
            )
        )
    return material_indices, issues


def _scan_gcode_line(
    line: bytes,
    material_indices: set[int],
    issues: list[PrintPlanIssue],
    *,
    plate_index: int,
) -> None:
    if len(line) > _MAX_GCODE_LINE_BYTES:
        raise InvalidThreeMfError("3MF plate G-code contains an excessively long line")
    match = _M620_RE.match(line)
    if match is None:
        return
    material_index = int(match.group(1))
    if material_index == 255:
        return
    if material_index > _MAX_MATERIAL_INDEX:
        if not any(
            issue.code == PrintPlanIssueCode.MATERIAL_INDEX_OUT_OF_RANGE and issue.plate_index == plate_index
            for issue in issues
        ):
            issues.append(
                PrintPlanIssue(
                    code=PrintPlanIssueCode.MATERIAL_INDEX_OUT_OF_RANGE,
                    severity=PrintPlanIssueSeverity.BLOCKING,
                    message=f"Plate references material index {material_index}, above the supported safety bound",
                    plate_index=plate_index,
                )
            )
        return
    material_indices.add(material_index)


def _project_material_metadata(
    archive: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
) -> tuple[dict[int, _ProjectMaterialMetadata], PrintPlanIssue | None]:
    candidates = [info for info in infos if info.filename == "Metadata/project_settings.config"]
    if not candidates:
        return {}, None
    if len(candidates) != 1:
        return {}, _project_metadata_issue("3MF contains ambiguous duplicate project_settings.config members")

    info = candidates[0]
    if info.flag_bits & 0x1:
        return {}, _project_metadata_issue("Encrypted project_settings.config metadata is not supported")
    if info.file_size > _MAX_PROJECT_SETTINGS_BYTES:
        return {}, _project_metadata_issue("project_settings.config exceeds the bounded metadata inspection limit")

    try:
        raw = archive.read(info)
        data = json.loads(raw.decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError, RuntimeError, NotImplementedError):
        return {}, _project_metadata_issue("project_settings.config could not be parsed safely")
    if not isinstance(data, dict):
        return {}, _project_metadata_issue("project_settings.config must contain a JSON object")

    families = _string_list(data.get("filament_type"))
    colors = _string_list(data.get("filament_colour"))
    profiles = _string_list(data.get("filament_settings_id"))
    count = min(max(len(families), len(colors), len(profiles)), _MAX_MATERIAL_INDEX + 1)

    result: dict[int, _ProjectMaterialMetadata] = {}
    for material_index in range(count):
        result[material_index] = _ProjectMaterialMetadata(
            material_family=_list_text(families, material_index),
            color_rgba_hex=_normalize_color(_list_text(colors, material_index)),
            profile_name=_list_text(profiles, material_index),
        )
    return result, None


def _string_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _list_text(values: list[object], index: int) -> str | None:
    if index >= len(values):
        return None
    value = values[index]
    return value.strip() if isinstance(value, str) and value.strip() else None


def _normalize_color(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.removeprefix("#").upper()
    if len(text) == 6 and all(ch in "0123456789ABCDEF" for ch in text):
        return f"{text}FF"
    if len(text) == 8 and all(ch in "0123456789ABCDEF" for ch in text):
        return text
    return None


def _project_metadata_issue(message: str) -> PrintPlanIssue:
    return PrintPlanIssue(
        code=PrintPlanIssueCode.PROJECT_METADATA_INVALID,
        severity=PrintPlanIssueSeverity.WARNING,
        message=message,
    )
