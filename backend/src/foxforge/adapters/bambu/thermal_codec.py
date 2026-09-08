# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Bambu-private thermal telemetry parsing.

Newly written FoxForge code informed by public Bambu LAN behavior and upstream
observations. Raw MQTT field names remain private to the Bambu adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite

from .native import BambuNativeThermalZone


class BambuThermalCodec:
    """Merge sparse Bambu heater reports without leaking wire fields upstream."""

    def __init__(self) -> None:
        self._zones: dict[str, BambuNativeThermalZone] = {}

    @property
    def zones(self) -> tuple[BambuNativeThermalZone, ...]:
        return tuple(sorted(self._zones.values(), key=lambda zone: (zone.position, zone.zone_id)))

    def apply(self, payload: object) -> tuple[BambuNativeThermalZone, ...]:
        if not isinstance(payload, Mapping):
            return self.zones
        print_data = payload.get("print")
        if not isinstance(print_data, Mapping):
            return self.zones

        dual_extruders = _dual_extruder_info(print_data)
        if dual_extruders is not None:
            self._merge_encoded_hotend("hotend:right", 0, dual_extruders[0].get("temp"))
            self._merge_encoded_hotend("hotend:left", 1, dual_extruders[1].get("temp"))
        else:
            self._merge_simple(
                "hotend:0",
                0,
                current=_present_temperature(print_data, "nozzle_temper"),
                target=_present_target(print_data, "nozzle_target_temper"),
            )
            secondary_current = _first_present_temperature(
                print_data,
                "nozzle_temper_2",
                "right_nozzle_temper",
            )
            secondary_target = _first_present_target(
                print_data,
                "nozzle_target_temper_2",
                "right_nozzle_target_temper",
            )
            self._merge_simple("hotend:1", 1, current=secondary_current, target=secondary_target)

        bed_encoded = _nested_temp(print_data, "device", "bed", "info", "temp")
        bed_current: object = _present_temperature(print_data, "bed_temper", maximum=200.0)
        bed_target: object = _present_target(print_data, "bed_target_temper", maximum=200.0)
        if bed_encoded is not _MISSING and bed_current is _MISSING and bed_target is _MISSING:
            bed_current, bed_target = _decode_encoded_or_direct(bed_encoded, maximum=200.0)
        self._merge_simple("bed", 10, current=bed_current, target=bed_target)

        chamber_current: object = _MISSING
        chamber_target: object = _MISSING
        if "chamber_temper" in print_data:
            chamber_current, decoded_target = _decode_encoded_or_direct(print_data.get("chamber_temper"), maximum=120.0)
            if decoded_target is not _MISSING:
                chamber_target = decoded_target
        chamber_explicit_target = _present_target(print_data, "chamber_target_temper", maximum=120.0)
        if chamber_explicit_target is not _MISSING:
            chamber_target = chamber_explicit_target

        ctc_temp = _nested_temp(print_data, "device", "ctc", "info", "temp")
        ctc_target = _nested_temp(print_data, "device", "ctc", "info", "target")
        if ctc_temp is not _MISSING and chamber_current is _MISSING:
            chamber_current, decoded_target = _decode_encoded_or_direct(ctc_temp, maximum=120.0)
            if chamber_target is _MISSING and decoded_target is not _MISSING:
                chamber_target = decoded_target
        if ctc_target is not _MISSING:
            explicit_target = _target_temperature(ctc_target, maximum=120.0)
            if explicit_target is not None:
                chamber_target = explicit_target
        self._merge_simple("chamber", 20, current=chamber_current, target=chamber_target)

        return self.zones

    def _merge_encoded_hotend(self, zone_id: str, position: int, value: object) -> None:
        if value is None:
            return
        current, target = _decode_encoded_or_direct(value, maximum=500.0, direct_target_zero=True)
        self._merge_simple(zone_id, position, current=current, target=target)

    def _merge_simple(self, zone_id: str, position: int, *, current: object, target: object) -> None:
        if current is _MISSING and target is _MISSING:
            return
        previous = self._zones.get(zone_id)
        current_value = previous.current_celsius if previous is not None else None
        target_value = previous.target_celsius if previous is not None else None
        if current is not _MISSING:
            current_value = current if isinstance(current, float) else None
        if target is not _MISSING:
            target_value = target if isinstance(target, float) else None
        if current_value is None and target_value is None:
            self._zones.pop(zone_id, None)
            return
        self._zones[zone_id] = BambuNativeThermalZone(
            zone_id=zone_id,
            position=position,
            current_celsius=current_value,
            target_celsius=target_value,
        )


class _Missing:
    pass


_MISSING = _Missing()


def _dual_extruder_info(print_data: Mapping[str, object]) -> tuple[Mapping[str, object], Mapping[str, object]] | None:
    device = print_data.get("device")
    if not isinstance(device, Mapping):
        return None
    extruder = device.get("extruder")
    if not isinstance(extruder, Mapping):
        return None
    info = extruder.get("info")
    if not isinstance(info, list) or len(info) < 2:
        return None
    entries = [entry for entry in info if isinstance(entry, Mapping)]
    if len(entries) < 2:
        return None
    by_id: dict[int, Mapping[str, object]] = {}
    for index, entry in enumerate(entries):
        raw_id = entry.get("id", index)
        identifier = _integer(raw_id)
        if identifier in {0, 1}:
            by_id[identifier] = entry
    if 0 not in by_id or 1 not in by_id:
        return None
    # Bambu H2/X2-family wire semantics: extruder 0 is right/default, 1 is left.
    return by_id[0], by_id[1]


def _nested_temp(mapping: Mapping[str, object], *path: str) -> object:
    current: object = mapping
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return _MISSING
        current = current[key]
    return current


def _present_temperature(mapping: Mapping[str, object], key: str, *, maximum: float = 500.0) -> object:
    if key not in mapping:
        return _MISSING
    value = _temperature(mapping.get(key), maximum=maximum)
    return value if value is not None else _MISSING


def _present_target(mapping: Mapping[str, object], key: str, *, maximum: float = 500.0) -> object:
    if key not in mapping:
        return _MISSING
    value = _target_temperature(mapping.get(key), maximum=maximum)
    return value if value is not None else _MISSING


def _first_present_temperature(mapping: Mapping[str, object], *keys: str) -> object:
    for key in keys:
        value = _present_temperature(mapping, key)
        if value is not _MISSING:
            return value
    return _MISSING


def _first_present_target(mapping: Mapping[str, object], *keys: str) -> object:
    for key in keys:
        value = _present_target(mapping, key)
        if value is not _MISSING:
            return value
    return _MISSING


def _decode_encoded_or_direct(
    value: object,
    *,
    maximum: float,
    direct_target_zero: bool = False,
) -> tuple[object, object]:
    numeric = _number(value)
    if numeric is None:
        return _MISSING, _MISSING
    if numeric > 500:
        encoded = int(numeric)
        target = encoded // 65536
        current = encoded % 65536
        current_value: object = float(current) if -50.0 < current < maximum else _MISSING
        target_value: object = float(target) if 0 <= target < maximum else _MISSING
        return current_value, target_value
    if not -50.0 < numeric < maximum:
        return _MISSING, _MISSING
    return numeric, 0.0 if direct_target_zero else _MISSING


def _temperature(value: object, *, maximum: float = 500.0) -> float | None:
    numeric = _number(value)
    return numeric if numeric is not None and -50.0 < numeric < maximum else None


def _target_temperature(value: object, *, maximum: float = 500.0) -> float | None:
    numeric = _number(value)
    return numeric if numeric is not None and 0.0 <= numeric < maximum else None


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        try:
            numeric = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    return numeric if isfinite(numeric) else None


def _integer(value: object) -> int | None:
    numeric = _number(value)
    if numeric is None or not numeric.is_integer():
        return None
    return int(numeric)
