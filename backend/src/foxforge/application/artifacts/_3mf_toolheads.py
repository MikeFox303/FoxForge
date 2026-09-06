# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Conservative Bambu 3MF toolhead expectation parsing.

This is newly written FoxForge code. Behavior is informed by Bambuddy's
plate-scoped nozzle mapping rules, while keeping the implementation bounded and
read-only for immutable staged artifacts.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass

_MAX_METADATA_BYTES = 4 * 1024 * 1024
_MAX_TOOLHEAD_POSITION = 31


@dataclass(frozen=True, slots=True)
class ToolheadMetadataWarning:
    plate_index: int
    message: str


def parse_bambu_toolhead_expectations(
    archive: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
    *,
    plate_indices: tuple[int, ...],
) -> tuple[dict[int, dict[int, int]], tuple[ToolheadMetadataWarning, ...]]:
    """Return zero-based project-material -> physical toolhead positions by plate.

    `slice_info.config` group assignments are treated as authoritative when
    present for a plate. `filament_nozzle_map` is only a fallback when that
    plate exposes no group assignment at all. Ambiguous/partial actual metadata
    suppresses fallback for that plate rather than guessing.

    Missing toolhead metadata is different from metadata that is present but
    unsafe to parse. The latter produces an explicit warning so the routing
    compiler cannot mistake parser failure for an unconstrained print plan.
    """

    settings, settings_error = _project_settings(archive, infos)
    if settings_error is not None:
        return {}, _warnings_for_plates(plate_indices, settings_error)
    if settings is None:
        return {}, ()

    if "physical_extruder_map" not in settings:
        return {}, ()
    physical_map = _physical_extruder_map(settings.get("physical_extruder_map"))
    if physical_map is None:
        return {}, _warnings_for_plates(
            plate_indices,
            "project_settings.config contains an invalid physical_extruder_map",
        )
    if len(physical_map) <= 1:
        return {}, ()

    fallback, fallback_error = _fallback_expectations(
        settings.get("filament_nozzle_map"),
        physical_map,
        present="filament_nozzle_map" in settings,
    )
    slice_root, slice_error = _slice_info_root(archive, infos)
    if slice_root is None:
        if slice_error is not None:
            return {}, _warnings_for_plates(plate_indices, slice_error)
        if fallback_error is not None:
            return {}, _warnings_for_plates(plate_indices, fallback_error)
        return {plate_index: dict(fallback) for plate_index in plate_indices}, ()

    results: dict[int, dict[int, int]] = {}
    warnings: list[ToolheadMetadataWarning] = []
    plates = slice_root.findall(".//plate")

    for plate_index in plate_indices:
        if plates:
            target = _plate_for_index(plates, plate_index + 1)
            if target is None:
                warnings.append(
                    ToolheadMetadataWarning(
                        plate_index,
                        "slice_info.config does not contain an unambiguous entry for this plate",
                    )
                )
                continue
        else:
            target = slice_root

        actual, state = _actual_plate_expectations(target, physical_map)
        if state == "actual":
            results[plate_index] = actual
        elif state == "fallback":
            if fallback_error is not None:
                warnings.append(ToolheadMetadataWarning(plate_index, fallback_error))
            else:
                results[plate_index] = dict(fallback)
        else:
            warnings.append(
                ToolheadMetadataWarning(
                    plate_index,
                    "slice_info.config contains partial or inconsistent toolhead assignments",
                )
            )

    return results, tuple(warnings)


def _warnings_for_plates(
    plate_indices: tuple[int, ...],
    message: str,
) -> tuple[ToolheadMetadataWarning, ...]:
    return tuple(ToolheadMetadataWarning(plate_index, message) for plate_index in plate_indices)


def _project_settings(
    archive: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
) -> tuple[dict[str, object] | None, str | None]:
    members = [info for info in infos if info.filename == "Metadata/project_settings.config"]
    if not members:
        return None, None
    if len(members) != 1:
        return None, "3MF contains ambiguous duplicate project_settings.config members"

    info = members[0]
    if info.flag_bits & 0x1:
        return None, "Encrypted project_settings.config metadata is not supported for toolhead routing"
    if info.file_size > _MAX_METADATA_BYTES:
        return None, "project_settings.config exceeds the bounded toolhead-metadata inspection limit"

    try:
        data = json.loads(archive.read(info).decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError, RuntimeError, NotImplementedError):
        return None, "project_settings.config could not be parsed safely for toolhead routing"
    if not isinstance(data, dict):
        return None, "project_settings.config must contain a JSON object for toolhead routing"
    return data, None


def _physical_extruder_map(value: object) -> tuple[int, ...] | None:
    if not isinstance(value, list) or not value:
        return None
    parsed: list[int] = []
    for item in value:
        number = _int_value(item)
        if number is None or not 0 <= number <= _MAX_TOOLHEAD_POSITION:
            return None
        parsed.append(number)
    return tuple(parsed)


def _fallback_expectations(
    value: object,
    physical_map: tuple[int, ...],
    *,
    present: bool,
) -> tuple[dict[int, int], str | None]:
    if not present:
        return {}, None
    if not isinstance(value, list):
        return {}, "project_settings.config contains an invalid filament_nozzle_map fallback"

    result: dict[int, int] = {}
    for material_index, item in enumerate(value):
        slicer_extruder = _int_value(item)
        if slicer_extruder is None or not 0 <= slicer_extruder < len(physical_map):
            return {}, "project_settings.config contains an invalid filament_nozzle_map fallback"
        result[material_index] = physical_map[slicer_extruder]
    return result, None


def _slice_info_root(
    archive: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
) -> tuple[ET.Element | None, str | None]:
    members = [info for info in infos if info.filename == "Metadata/slice_info.config"]
    if not members:
        return None, None
    if len(members) != 1:
        return None, "3MF contains ambiguous duplicate slice_info.config members"

    info = members[0]
    if info.flag_bits & 0x1:
        return None, "Encrypted slice_info.config metadata is not supported"
    if info.file_size > _MAX_METADATA_BYTES:
        return None, "slice_info.config exceeds the bounded toolhead-metadata inspection limit"

    try:
        raw = archive.read(info)
    except (KeyError, RuntimeError, NotImplementedError):
        return None, "slice_info.config could not be read safely"

    upper = raw.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        return None, "slice_info.config contains forbidden DTD/entity declarations"

    try:
        return ET.fromstring(raw), None
    except ET.ParseError:
        return None, "slice_info.config is not valid bounded XML"


def _plate_for_index(plates: list[ET.Element], plate_number: int) -> ET.Element | None:
    matches: list[ET.Element] = []
    for plate in plates:
        for metadata in plate.findall("metadata"):
            if metadata.get("key") != "index":
                continue
            if _int_value(metadata.get("value")) == plate_number:
                matches.append(plate)
                break
    return matches[0] if len(matches) == 1 else None


def _actual_plate_expectations(
    plate: ET.Element,
    physical_map: tuple[int, ...],
) -> tuple[dict[int, int], str]:
    filaments = plate.findall(".//filament")
    if not filaments:
        return {}, "fallback"

    grouped: list[tuple[int, int]] = []
    ungrouped = 0
    seen_groups: dict[int, int] = {}
    for filament in filaments:
        filament_id = _int_value(filament.get("id"))
        group_id = _int_value(filament.get("group_id"))
        if filament_id is None or filament_id <= 0:
            continue
        material_index = filament_id - 1
        if filament.get("group_id") is None:
            ungrouped += 1
            continue
        if group_id is None or group_id < 0:
            return {}, "ambiguous"
        previous = seen_groups.setdefault(material_index, group_id)
        if previous != group_id:
            return {}, "ambiguous"
        grouped.append((material_index, group_id))

    if not grouped:
        return {}, "fallback"
    if ungrouped:
        return {}, "ambiguous"

    group_table, table_state = _group_extruder_indices(plate)
    if table_state == "invalid":
        return {}, "ambiguous"

    result: dict[int, int] = {}
    for material_index, group_id in grouped:
        slicer_extruder = group_id if group_table is None else group_table.get(group_id)
        if slicer_extruder is None or not 0 <= slicer_extruder < len(physical_map):
            return {}, "ambiguous"
        target = physical_map[slicer_extruder]
        if result.setdefault(material_index, target) != target:
            return {}, "ambiguous"
    return result, "actual"


def _group_extruder_indices(plate: ET.Element) -> tuple[dict[int, int] | None, str]:
    table: dict[int, int] = {}
    for nozzle in plate.findall(".//nozzle"):
        group_id = _int_value(nozzle.get("id"))
        extruder_id = _int_value(nozzle.get("extruder_id"))
        if group_id is None or group_id < 0 or extruder_id is None or extruder_id <= 0:
            return None, "invalid"
        extruder_index = extruder_id - 1
        if table.setdefault(group_id, extruder_index) != extruder_index:
            return None, "invalid"
    return (table or None), "ok"


def _int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None
