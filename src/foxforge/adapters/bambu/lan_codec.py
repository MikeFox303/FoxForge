# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Pure Bambu LAN MQTT payload translation.

This is newly written FoxForge code based on publicly documented Bambu LAN
protocol semantics. It deliberately keeps MQTT field names inside the Bambu
adapter package and does not depend on Bambuddy implementation modules.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from foxforge.domain.printers import utc_now

from .native import (
    BambuMaterialUnitKind,
    BambuNativeFault,
    BambuNativeMaterialRoute,
    BambuNativeMaterialUnit,
    BambuNativePrintRequest,
    BambuNativeState,
    BambuNativeTray,
)

_ACTIVE_PRINT_STATES = frozenset({"PREPARE", "SLICING", "RUNNING", "PAUSE"})
_MODULE_KIND_PREFIXES = {
    "ams/": BambuMaterialUnitKind.AMS,
    "n3f/": BambuMaterialUnitKind.AMS_2_PRO,
    "n3s/": BambuMaterialUnitKind.AMS_HT,
}


class BambuLanCodec:
    """Merge incremental Bambu MQTT reports into one complete native state."""

    def __init__(self) -> None:
        self._unit_kinds: dict[int, BambuMaterialUnitKind] = {}
        self._state = BambuNativeState(
            connected=False,
            gcode_state=None,
            current_print=None,
            vendor_job_id=None,
            progress_percent=None,
            remaining_minutes=None,
            layer_num=None,
            total_layers=None,
            faults=(),
            material_units=(),
            observed_at=utc_now(),
        )

    @property
    def state(self) -> BambuNativeState:
        return self._state

    def mark_connected(self, connected: bool) -> BambuNativeState:
        self._state = replace(self._state, connected=connected, observed_at=utc_now())
        return self._state

    def apply(self, payload: object) -> BambuNativeState | None:
        if not isinstance(payload, dict):
            return None

        version_changed = False
        info = payload.get("info")
        if isinstance(info, dict) and info.get("command") == "get_version":
            version_changed = self._apply_version(info)

        print_data = payload.get("print")
        if not isinstance(print_data, dict):
            return self._state if version_changed else None
        command = print_data.get("command")
        if command not in {None, "push_status"} and not _contains_status_fields(print_data):
            return self._state if version_changed else None

        previous = self._state
        updates: dict[str, object] = {"connected": True, "observed_at": utc_now()}
        _copy_if_present(print_data, "gcode_state", updates, "gcode_state", _optional_string)
        _copy_if_present(print_data, "subtask_name", updates, "current_print", _optional_string)
        if "subtask_name" not in print_data:
            _copy_if_present(print_data, "gcode_file", updates, "current_print", _optional_string)
        if "subtask_id" in print_data or "task_id" in print_data:
            job_id = print_data.get("subtask_id") or print_data.get("task_id")
            updates["vendor_job_id"] = _optional_identifier(job_id)
        _copy_if_present(print_data, "mc_percent", updates, "progress_percent", _bounded_percent)
        _copy_if_present(print_data, "mc_remaining_time", updates, "remaining_minutes", _nonnegative_int)
        _copy_if_present(print_data, "layer_num", updates, "layer_num", _nonnegative_int)
        _copy_if_present(print_data, "total_layer_num", updates, "total_layers", _nonnegative_int)

        faults = _parse_faults(print_data)
        if faults is not None:
            updates["faults"] = faults

        material_units = self._parse_material_units(print_data)
        if material_units is not None:
            updates["material_units"] = material_units

        current = replace(previous, **updates)
        self._state = current
        return current

    def _apply_version(self, info: dict[str, object]) -> bool:
        modules = info.get("module")
        if not isinstance(modules, list):
            return False
        changed = False
        for module in modules:
            if not isinstance(module, dict):
                continue
            name = module.get("name")
            if not isinstance(name, str):
                continue
            for prefix, kind in _MODULE_KIND_PREFIXES.items():
                if not name.startswith(prefix):
                    continue
                unit_id = _int_value(name.removeprefix(prefix))
                if unit_id is not None and self._unit_kinds.get(unit_id) != kind:
                    self._unit_kinds[unit_id] = kind
                    changed = True
                break
        if changed and self._state.material_units:
            self._state = replace(
                self._state,
                material_units=tuple(
                    replace(unit, kind=self._unit_kinds.get(unit.ams_id, unit.kind))
                    for unit in self._state.material_units
                ),
                observed_at=utc_now(),
            )
        return changed

    def _parse_material_units(self, print_data: dict[str, object]) -> tuple[BambuNativeMaterialUnit, ...] | None:
        touched = False
        units: list[BambuNativeMaterialUnit] = []
        ams_data = print_data.get("ams")
        if isinstance(ams_data, dict):
            raw_units = ams_data.get("ams")
            if isinstance(raw_units, list):
                touched = True
                tray_now = _int_value(ams_data.get("tray_now"))
                exist_bits = _hex_or_int(ams_data.get("tray_exist_bits"))
                for raw_unit in raw_units:
                    unit = self._parse_ams_unit(raw_unit, tray_now=tray_now, exist_bits=exist_bits)
                    if unit is not None:
                        units.append(unit)

        vt_tray = print_data.get("vt_tray")
        if isinstance(vt_tray, dict):
            touched = True
            external = self._parse_external_tray(vt_tray)
            if external is not None:
                units.append(external)

        if not touched:
            return None
        return tuple(sorted(units, key=lambda item: item.ams_id))

    def _parse_ams_unit(
        self,
        raw_unit: object,
        *,
        tray_now: int | None,
        exist_bits: int | None,
    ) -> BambuNativeMaterialUnit | None:
        if not isinstance(raw_unit, dict):
            return None
        ams_id = _int_value(raw_unit.get("id"))
        if ams_id is None:
            return None
        raw_trays = raw_unit.get("tray")
        trays: list[BambuNativeTray] = []
        if isinstance(raw_trays, list):
            for raw_tray in raw_trays:
                tray = _parse_tray(raw_tray, ams_id=ams_id, tray_now=tray_now, exist_bits=exist_bits)
                if tray is not None:
                    trays.append(tray)
        return BambuNativeMaterialUnit(
            ams_id=ams_id,
            kind=self._unit_kinds.get(ams_id, _default_unit_kind(ams_id)),
            label=f"AMS {ams_id + 1}" if ams_id >= 0 else None,
            trays=tuple(sorted(trays, key=lambda item: item.tray_id)),
        )

    def _parse_external_tray(self, raw_tray: dict[str, object]) -> BambuNativeMaterialUnit | None:
        ams_id = _int_value(raw_tray.get("id"))
        if ams_id is None:
            ams_id = 254
        tray = BambuNativeTray(
            ams_id=ams_id,
            tray_id=0,
            material_type=_optional_string(raw_tray.get("tray_type")),
            vendor_name=None,
            product_name=_optional_string(raw_tray.get("tray_sub_brands")),
            color_rgba=_optional_string(raw_tray.get("tray_color")),
            tag_uid=_clean_tag(raw_tray.get("tag_uid")),
            remaining_percent=_bounded_percent(raw_tray.get("remain")),
            exists=_external_exists(raw_tray),
            active=None,
        )
        return BambuNativeMaterialUnit(
            ams_id=ams_id,
            kind=BambuMaterialUnitKind.EXTERNAL,
            label="External spool",
            trays=(tray,),
        )


def is_bambu_busy(state: BambuNativeState) -> bool:
    return (state.gcode_state or "").strip().upper() in _ACTIVE_PRINT_STATES


def build_pushall_command(sequence_id: str) -> dict[str, object]:
    return {
        "pushing": {
            "sequence_id": sequence_id,
            "command": "pushall",
            "version": 1,
            "push_target": 1,
        }
    }


def build_get_version_command(sequence_id: str) -> dict[str, object]:
    return {"info": {"sequence_id": sequence_id, "command": "get_version"}}


def build_project_file_command(
    sequence_id: str,
    request: BambuNativePrintRequest,
    remote_filename: str,
) -> dict[str, object]:
    plate_number = request.plate_number or 1
    routes = tuple(sorted(request.material_routes, key=lambda route: route.material_index))
    ams_mapping = _ams_mapping(routes)
    ams_mapping2 = [{"ams_id": route.ams_id, "slot_id": route.tray_id} for route in routes if 0 <= route.ams_id < 254]
    use_ams = bool(ams_mapping2)
    subtask_name = (request.requested_name or Path(remote_filename).stem).strip() or Path(remote_filename).stem
    return {
        "print": {
            "sequence_id": sequence_id,
            "command": "project_file",
            "param": f"Metadata/plate_{plate_number}.gcode",
            "project_id": "0",
            "profile_id": "0",
            "task_id": "0",
            "subtask_id": "0",
            "subtask_name": subtask_name,
            "file": remote_filename,
            "url": f"ftp:///{remote_filename}",
            "md5": "",
            "timelapse": False,
            "bed_type": "auto",
            "bed_leveling": True,
            "bed_levelling": True,
            "flow_cali": True,
            "vibration_cali": True,
            "layer_inspect": False,
            "use_ams": use_ams,
            "ams_mapping": ams_mapping,
            "ams_mapping2": ams_mapping2,
        }
    }


def _ams_mapping(routes: tuple[BambuNativeMaterialRoute, ...]) -> list[int]:
    if not routes:
        return []
    max_index = max(route.material_index for route in routes)
    result = [-1] * (max_index + 1)
    for route in routes:
        if route.material_index < 0:
            continue
        result[route.material_index] = route.ams_id * 4 + route.tray_id if 0 <= route.ams_id < 254 else -1
    return result


def _parse_tray(
    raw_tray: object,
    *,
    ams_id: int,
    tray_now: int | None,
    exist_bits: int | None,
) -> BambuNativeTray | None:
    if not isinstance(raw_tray, dict):
        return None
    tray_id = _int_value(raw_tray.get("id"))
    if tray_id is None:
        return None
    global_tray = ams_id * 4 + tray_id
    exists = None
    if exist_bits is not None and 0 <= global_tray < 256:
        exists = bool((exist_bits >> global_tray) & 1)
    elif "state" in raw_tray:
        state = _int_value(raw_tray.get("state"))
        if state is not None:
            exists = state not in {9, 10}
    active = None if tray_now is None else tray_now in {tray_id, global_tray}
    return BambuNativeTray(
        ams_id=ams_id,
        tray_id=tray_id,
        material_type=_optional_string(raw_tray.get("tray_type")),
        vendor_name=None,
        product_name=_optional_string(raw_tray.get("tray_sub_brands")),
        color_rgba=_optional_string(raw_tray.get("tray_color")),
        tag_uid=_clean_tag(raw_tray.get("tag_uid")),
        remaining_percent=_bounded_percent(raw_tray.get("remain")),
        exists=exists,
        active=active,
    )


def _parse_faults(print_data: dict[str, object]) -> tuple[BambuNativeFault, ...] | None:
    touched = "print_error" in print_data or "hms" in print_data
    if not touched:
        return None
    faults: list[BambuNativeFault] = []
    print_error = _int_value(print_data.get("print_error"))
    if print_error:
        faults.append(
            BambuNativeFault(
                code=f"{print_error:08X}",
                severity="error",
                message="Bambu print error",
            )
        )
    hms = print_data.get("hms")
    if isinstance(hms, list):
        for entry in hms:
            if not isinstance(entry, dict):
                continue
            code = entry.get("code", entry.get("attr"))
            if code in {None, 0, "0", ""}:
                continue
            faults.append(
                BambuNativeFault(
                    code=str(code),
                    severity="error",
                    message=_optional_string(entry.get("msg")),
                )
            )
    return tuple(faults)


def _contains_status_fields(print_data: dict[str, object]) -> bool:
    fields = {
        "gcode_state",
        "subtask_name",
        "gcode_file",
        "mc_percent",
        "mc_remaining_time",
        "layer_num",
        "total_layer_num",
        "ams",
        "vt_tray",
        "print_error",
        "hms",
    }
    return any(field in print_data for field in fields)


def _copy_if_present(
    source: dict[str, object],
    source_key: str,
    target: dict[str, object],
    target_key: str,
    converter: Callable[[object], object],
) -> None:
    if source_key in source:
        target[target_key] = converter(source.get(source_key))


def _optional_string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_identifier(value: object) -> str | None:
    if value in {None, "", 0, "0"}:
        return None
    return str(value)


def _int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _nonnegative_int(value: object) -> int | None:
    number = _int_value(value)
    return number if number is not None and number >= 0 else None


def _bounded_percent(value: object) -> int | None:
    number = _int_value(value)
    return number if number is not None and 0 <= number <= 100 else None


def _hex_or_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip(), 16)
        except ValueError:
            return None
    return None


def _clean_tag(value: object) -> str | None:
    text = _optional_string(value)
    if text is None or set(text) <= {"0"}:
        return None
    return text


def _external_exists(raw_tray: dict[str, object]) -> bool | None:
    state = _int_value(raw_tray.get("state"))
    if state is not None:
        return state not in {9, 10}
    return True if any(raw_tray.get(key) for key in ("tray_type", "tray_color", "tag_uid")) else None


def _default_unit_kind(ams_id: int) -> BambuMaterialUnitKind:
    if 128 <= ams_id <= 135:
        return BambuMaterialUnitKind.AMS_HT
    return BambuMaterialUnitKind.AMS
