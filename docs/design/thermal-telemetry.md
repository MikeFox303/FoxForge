# Thermal telemetry capability

SPDX-License-Identifier: AGPL-3.0-only  
Copyright (C) 2026 MikeFox303

## Status

Candidate 6 design decision for `foxforge.thermal_telemetry` major version 1.

## Decision

Temperature telemetry is a **separate optional printer capability**, not a field on the generic `PrinterSnapshot`.

The common contract exposes only normalized thermal zones:

- `zoneId` — stable FoxForge-local identity such as `hotend:0`, `bed:0`, or `chamber:0`;
- `kind` — `hotend`, `bed`, `chamber`, or `other`;
- `position` — non-negative stable ordering within the adapter;
- optional presentation `label`;
- `currentCelsius` and/or `targetCelsius`;
- snapshot `observedAt` and `stale`.

A zone must contain at least one finite current/target value. Capability descriptors declare whether target temperatures are reported.

This keeps the base printer snapshot small and vendor-independent while allowing adapters with richer telemetry to expose it without lowering Bambu support to a lowest-common-denominator interface.

## Adapter boundary

Raw vendor fields and object names remain inside their adapter packages.

### Bambu Lab

The Bambu adapter owns MQTT/wire details such as `nozzle_temper`, `bed_temper`, `chamber_temper`, and X2/H2-family `device.extruder.info`.

For dual-toolhead X2/H2-family reports:

- wire extruder `id=0` maps to FoxForge `hotend:0` (right/default toolhead);
- wire extruder `id=1` maps to FoxForge `hotend:1` (left toolhead);
- encoded target/current values are decoded inside the Bambu codec only.

Bambu reports are sparse. Missing or malformed thermal values do not erase the last valid value in the current connection epoch. The codec is reset on reconnect so values from an old connection are never presented as fresh data for a new one.

### Moonraker / Klipper

Moonraker exposes a list of loaded Klipper printer objects. FoxForge discovers that list only after Klippy reports `ready`, then extends its existing subscription with thermal fields for objects that actually exist:

- `extruder`, `extruder1`, ... → `hotend:0`, `hotend:1`, ...;
- `heater_bed` → `bed:0`.

Only `temperature` and `target` are subscribed. Moonraker status notifications are sparse diffs, so the transport merges them into accumulated connection-local status before creating a native snapshot.

FoxForge does **not** infer chamber support from arbitrary `temperature_sensor *` names in v1. A future chamber implementation must use explicit configuration/discovery semantics rather than guessing by model or sensor name.

## Staleness and reconnect behavior

- A connected adapter reports `stale=false`.
- If a connection is lost after thermal zones were observed, the last snapshot may remain available with `stale=true` until the next connection epoch.
- Reconnect establishes a new transport state from the new subscription response; old connection-local values must not be silently promoted to fresh data.
- Empty thermal capability state does not produce reconnect event noise by itself.

## Frontend and API rules

The API serializes only the common capability descriptor and normalized thermal snapshot. Frontend code consumes those FoxForge types and must not inspect Bambu MQTT keys, Moonraker object names, or printer model strings to decide thermal behavior.

The same `ThermalTelemetry` presentation components therefore work for Bambu and Moonraker printers.

## Provenance

The implementation is newly written FoxForge code. Behavior was informed by:

- observed/sanitized Bambu X2D reports and public Bambu LAN behavior;
- upstream Bambu ecosystem observations used as behavioral references, without copying application code;
- Moonraker's documented `printer.objects.list`, `printer.objects.subscribe`, `extruder`, and `heater_bed` contracts.

No upstream source code is copied into this capability.

## Acceptance coverage

Candidate 6 requires tests proving:

- Bambu dual hotend/bed/chamber normalization;
- sparse Bambu updates preserve unrelated and previously valid values;
- malformed/non-finite Bambu thermal values cannot crash parsing or erase valid state;
- an empty dual-extruder report does not fabricate zones;
- Moonraker subscribes only to discovered thermal objects;
- Moonraker sparse temperature updates preserve prior targets;
- multiple Klipper extruders keep deterministic positions;
- common thermal events/read models contain no raw vendor field names;
- frontend rendering remains capability-driven and vendor-independent.
